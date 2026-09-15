from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from json import dumps as json_dumps
from re import match as re_match
from re import sub as re_sub
from uuid import uuid4

from fastapi import HTTPException

from config.settings import settings
from integrations.amazon_creators_client import (
    AmazonCatalogItem,
    AmazonCreatorsError,
    is_amazon_catalog_configured,
    lookup_amazon_item,
)
from integrations.browser_fetcher import fetch_html_with_browser
from integrations.html_fetcher import HtmlDocument, HtmlFetchError, fetch_public_html
from utils.cache import get_cache_service
from web_extract.amazon_url import extract_amazon_asin
from web_extract.completeness import extract_needs_another_pass, merge_extract_data
from web_extract.candidate_filter import (
    clean_candidate_map,
    data_from_candidates,
    harvest_article_headings,
    harvest_content_headings,
    merge_heading_candidates,
    needs_browser_render,
)
from web_extract.command_planner import CommandPlannerError, plan_extract_commands
from web_extract.dtos.web_extract import (
    ExtractCommand,
    WebExtractError,
    WebExtractMeta,
    WebExtractOutcome,
    WebExtractRequest,
    WebExtractResponse,
    WebExtractResult,
)
from web_extract.extract_plan import (
    MAX_CHILD_PROMPT_CHARS,
    ExtractPlan,
    PageSignals,
    heuristic_extract_plan,
    plan_extract_job,
    signals_from_url,
)
from web_extract.chunk_extractor import extract_from_chunk
from web_extract.input_refiner import refine_user_prompt
from web_extract.output_normalizer import normalize_extract_output
from web_extract.output_checker import (
    CONFIDENCE_THRESHOLD,
    MAX_OUTPUT_ATTEMPTS,
    OutputCheck,
    check_extract_output,
    heuristic_output_check,
    kept_extract,
)
from web_extract.extract_executor import collect_extract_candidates, execute_extract_commands
from web_extract.extract_refiner import ExtractRefineError, refine_extract_data
from web_extract.link_inventory import collect_link_inventory, extract_profile_links
from web_extract.plain_text_chunks import chunk_plain_text, sanitize_to_plain_text
from web_extract.regex_extractors import apply_regex_rules
from web_extract.llms_txt import (
    LLMS_REGION_KEY,
    attach_llms_txt_region,
    fetch_same_origin_llms_txt,
)
from web_extract.region_index import (
    build_region_index,
    compact_region_index,
    format_slices,
    slice_prompt_windows,
    slice_selected_regions,
)
from web_extract.region_planner import plan_relevant_regions
from web_extract.slice_extractor import extract_from_slices
from web_extract.html_sanitizer import (
    build_dom_outline,
    looks_like_access_wall,
    page_title,
    sanitize_html,
)


@dataclass
class WebExtractContext:
    cache: object | None = None
    fetch_browser: Callable[[str], HtmlDocument] | None = None
    fetch_html: Callable[[str], HtmlDocument] | None = None
    lookup_amazon_item: Callable[[str], AmazonCatalogItem | None] | None = None
    now: Callable[[], datetime] | None = None
    plan_commands: Callable[[str, str, str], list[ExtractCommand]] | None = None
    plan_regions: Callable[[str, str, str, set[str]], list[str]] | None = None
    extract_slices: Callable[[str, str, str], dict] | None = None
    fetch_llms_txt: Callable[[str], str | None] | None = None
    plan_job: Callable[[str, PageSignals], ExtractPlan] | None = None
    check_output: Callable[[str, dict], OutputCheck] | None = None
    refine_prompt: Callable[[str, str], str] | None = None
    extract_chunk: Callable[[str, str, str, dict, dict], dict] | None = None
    normalize_output: Callable[[str, str, dict, dict], dict] | None = None
    refine_data: Callable[[str, str, dict], dict] | None = None
    use_amazon_catalog: bool = True
    use_browser_fallback: bool = True
    use_refine: bool = True
    use_regions: bool = True
    uuid: Callable[[], str] | None = None


AMAZON_CATALOG_COMMANDS = [
    ExtractCommand(name="name", selector="amazon-creators:itemInfo.title", attr="text", many=False),
    ExtractCommand(name="price", selector="amazon-creators:offersV2.listings.price", attr="text", many=False),
]
AMAZON_PAGE_COMMANDS = [
    ExtractCommand(name="name", selector="#productTitle", attr="text", many=False),
    ExtractCommand(name="price", selector=".a-price .a-offscreen", attr="text", many=False),
]


class WebExtractService:
    def _merge_commands(
        self,
        *groups: list[ExtractCommand],
    ) -> list[ExtractCommand]:
        merged: list[ExtractCommand] = []
        seen: set[tuple[str, str, str, bool]] = set()
        for group in groups:
            for command in group:
                fingerprint = (
                    command.name,
                    command.selector,
                    command.attr,
                    command.many,
                )
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                merged.append(command)
        return merged

    def _resolve_idempotency_key(self, payload: WebExtractRequest) -> str:
        if payload.idempotency_key:
            return payload.idempotency_key
        fingerprint = f"{payload.url}|{payload.prompt.strip().lower()}"
        return sha256(fingerprint.encode("utf-8")).hexdigest()

    def _build_outcome(
        self,
        *,
        status: bool,
        message: str,
        status_code: int,
        result: WebExtractResult | None,
        errors: list[WebExtractError],
        meta: WebExtractMeta,
    ) -> WebExtractOutcome:
        return WebExtractOutcome(
            status_code=status_code,
            body=WebExtractResponse(
                status=status,
                message=message,
                result=result,
                meta=meta,
                errors=errors,
            ),
        )

    def _store_and_succeed(
        self,
        *,
        cache,
        cache_key: str,
        meta: Callable,
        result: WebExtractResult,
        provider: str,
    ) -> WebExtractOutcome:
        response_meta = meta(provider=provider, confidence=result.confidence)
        if cache is not None:
            cache.set_json(
                cache_key,
                {
                    "meta": response_meta.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                },
                ttl_seconds=settings.runtime.cache.default_ttl_seconds,
            )
        return self._build_outcome(
            status=True,
            message="Page extracted",
            status_code=200,
            result=result,
            errors=[],
            meta=response_meta,
        )

    def _blocked_outcome(self, meta: Callable, provider: str = "local-html") -> WebExtractOutcome:
        return self._build_outcome(
            status=False,
            message="The page did not contain extractable page data.",
            status_code=422,
            result=None,
            errors=[
                WebExtractError(
                    code="FETCH_BLOCKED",
                    message="The downloaded page looks like an access wall, not the requested content.",
                    retriable=True,
                )
            ],
            meta=meta(provider=provider),
        )

    def _region_commands(self, keys: list[str]) -> list[ExtractCommand]:
        commands: list[ExtractCommand] = []
        for key in keys:
            name = re_sub(r"[^A-Za-z0-9_]", "", key)
            if not name or not name[0].isalpha():
                name = f"region{name}"
            selector = f"#{key}" if re_match(r"^[A-Za-z][\w-]*$", key) else key
            commands.append(
                ExtractCommand(name=name[:64], selector=selector[:256], attr="html", many=False)
            )
        return commands

    def _resolve_browser_fetch(self, ctx: WebExtractContext):
        if ctx.fetch_browser is not None:
            return ctx.fetch_browser
        if ctx.use_browser_fallback and settings.web_extract_browser_fallback:
            return fetch_html_with_browser
        return None

    def _prepare_candidates(self, html: str, commands: list[ExtractCommand]) -> dict:
        css_candidates = collect_extract_candidates(html, commands)
        headings = harvest_content_headings(html)
        article_headings = harvest_article_headings(html)
        return clean_candidate_map(
            merge_heading_candidates(commands, css_candidates, headings, article_headings)
        )

    def _catalog_seed(self, ctx: WebExtractContext, url: str) -> tuple[dict, list[ExtractCommand], str | None]:
        asin = extract_amazon_asin(url)
        lookup = ctx.lookup_amazon_item
        if lookup is None and ctx.use_amazon_catalog and is_amazon_catalog_configured():
            lookup = lookup_amazon_item
        if not asin or lookup is None:
            return {}, [], None
        try:
            item = lookup(asin)
        except AmazonCreatorsError:
            item = None
        if not item or not item.name:
            return {}, [], None
        data = {"name": item.name}
        if item.price:
            data["price"] = item.price
        return data, AMAZON_CATALOG_COMMANDS[: len(data)], "amazon-creators"

    def _page_seed(self, html: str, url: str) -> tuple[dict, list[ExtractCommand]]:
        if not extract_amazon_asin(url) or looks_like_access_wall(html):
            return {}, []
        data = execute_extract_commands(html, AMAZON_PAGE_COMMANDS)
        if not data.get("name"):
            return {}, []
        return data, AMAZON_PAGE_COMMANDS[: len(data)]

    def _empty_outcome(
        self,
        meta: Callable,
        provider: str,
        commands: list[ExtractCommand] | None = None,
        url: str | None = None,
    ) -> WebExtractOutcome:
        return self._build_outcome(
            status=False,
            message="The page did not contain extractable page data.",
            status_code=422,
            result=(
                None
                if url is None
                else WebExtractResult(url=url, data={}, commands=commands or [])
            ),
            errors=[
                WebExtractError(
                    code="EXTRACT_EMPTY",
                    message="The extraction commands did not match any page content."
                    if commands
                    else "The downloaded page did not contain usable text.",
                    retriable=True,
                )
            ],
            meta=meta(provider=provider),
        )

    def _low_confidence_outcome(
        self,
        meta: Callable,
        provider: str,
        *,
        url: str,
        data: dict,
        commands: list[ExtractCommand],
        confidence: float,
    ) -> WebExtractOutcome:
        return self._build_outcome(
            status=False,
            message="The page did not contain a confident extract for the requested data.",
            status_code=422,
            result=WebExtractResult(
                url=url,
                data=data,
                commands=commands,
                confidence=confidence,
            ),
            errors=[
                WebExtractError(
                    code="LOW_CONFIDENCE_EXTRACT",
                    message="The extractor found partial evidence, but confidence stayed below the acceptance threshold.",
                    retriable=True,
                )
            ],
            meta=meta(provider=provider, confidence=confidence),
        )

    def _resolve_plan(
        self,
        ctx: WebExtractContext,
        prompt: str,
        signals: PageSignals,
        *,
        allow_llm: bool,
    ) -> ExtractPlan:
        if ctx.plan_job is not None:
            return ctx.plan_job(prompt, signals)
        if allow_llm:
            try:
                return plan_extract_job(prompt, signals)
            except (CommandPlannerError, HTTPException):
                return heuristic_extract_plan(prompt, signals)
        return heuristic_extract_plan(prompt, signals)

    def _refine_request_prompt(
        self,
        ctx: WebExtractContext,
        *,
        prompt: str,
        url: str,
    ) -> str:
        refiner = ctx.refine_prompt
        try:
            refined = (
                refiner(prompt, url)
                if refiner is not None
                else refine_user_prompt(prompt, url)
            )
        except HTTPException:
            raise
        except Exception:
            return prompt.strip()
        if not isinstance(refined, str) or not refined.strip():
            return prompt.strip()
        return refined.strip()

    def _incomplete(self, prompt: str, data: dict, plan: ExtractPlan) -> bool:
        return extract_needs_another_pass(prompt, data, plan.fields)

    def _score_output(
        self,
        ctx: WebExtractContext,
        prompt: str,
        url: str,
        data: dict,
        plan: ExtractPlan,
    ) -> OutputCheck:
        checker = ctx.check_output
        if checker is not None:
            return checker(prompt, data)
        try:
            return check_extract_output(
                prompt,
                url,
                data,
                expected_output=plan.expected_output,
                verification_rules=plan.verification_rules,
            )
        except (CommandPlannerError, HTTPException):
            return heuristic_output_check(prompt, data)

    def _plan_with_retry(self, plan: ExtractPlan, verdict: OutputCheck, kept: dict) -> ExtractPlan:
        missing = ", ".join(verdict.missing) or verdict.reason or "requested fields"
        accepted = json_dumps(kept, ensure_ascii=False)
        if len(accepted) > 500:
            accepted = f"{accepted[:500]}..."
        base = plan.child_prompt.split("Accepted findings to keep unchanged:", 1)[0]
        base = base.split("Fill missing or weak fields:", 1)[0].strip()
        note = (
            f"Fill missing or weak fields: {missing}.\n"
            f"Accepted findings to keep unchanged: {accepted}\n"
            f"Checker: {verdict.reason or f'confidence {verdict.confidence:.2f} below {CONFIDENCE_THRESHOLD}'}.\n"
            "Reuse accepted values unchanged. Search only for the missing fields."
        )
        return ExtractPlan(
            site_type=plan.site_type,
            intent=plan.intent,
            child_prompt=f"{note}\n\n{base}"[:MAX_CHILD_PROMPT_CHARS],
            fields=plan.fields,
            tools=plan.tools,
            constraints=plan.constraints,
            expected_output=plan.expected_output,
            verification_rules=plan.verification_rules,
            ids=plan.ids,
            close_url_formats=plan.close_url_formats,
            regex_rules=plan.regex_rules,
            what_not_to_do=plan.what_not_to_do,
        )

    def _extract_from_plain_text(
        self,
        *,
        ctx: WebExtractContext,
        plan: ExtractPlan,
        url: str,
        html: str,
        seed: dict,
    ) -> tuple[dict, list[ExtractCommand]]:
        plain_text = sanitize_to_plain_text(html)
        chunks = chunk_plain_text(plain_text)[:8]
        if not chunks:
            return dict(seed), []

        extractor = ctx.extract_chunk
        data = dict(seed)
        commands: list[ExtractCommand] = []
        for index, chunk in enumerate(chunks, start=1):
            regex_data = apply_regex_rules(chunk, plan.regex_rules)
            if regex_data:
                data = merge_extract_data(data, regex_data)
            try:
                incoming = (
                    extractor(
                        plan.child_prompt,
                        url,
                        chunk,
                        regex_data,
                        plan.expected_output,
                    )
                    if extractor is not None
                    else extract_from_chunk(
                        url=url,
                        chunk=chunk,
                        strategy_prompt=plan.child_prompt,
                        expected_output=plan.expected_output,
                        regex_hits=regex_data,
                    )
                )
            except HTTPException:
                raise
            except Exception:
                incoming = {}
            if incoming:
                data = merge_extract_data(data, incoming)
            if regex_data or incoming:
                commands.append(
                    ExtractCommand(
                        name=f"chunk{index}",
                        selector=f"text-chunk-{index}",
                        attr="text",
                        many=False,
                    )
                )
        return data, commands

    def _normalize_data(
        self,
        ctx: WebExtractContext,
        *,
        prompt: str,
        url: str,
        plan: ExtractPlan,
        data: dict,
    ) -> dict:
        if not data:
            return data
        normalizer = ctx.normalize_output
        try:
            normalized = (
                normalizer(prompt, url, plan.expected_output, data)
                if normalizer is not None
                else normalize_extract_output(
                    url=url,
                    user_prompt=prompt,
                    expected_output=plan.expected_output,
                    extracted_data=data,
                )
            )
        except HTTPException:
            raise
        except Exception:
            return data
        return normalized if isinstance(normalized, dict) and normalized else data

    def _extract_from_evidence(
        self,
        *,
        ctx: WebExtractContext,
        plan: ExtractPlan,
        url: str,
        html: str,
        seed: dict,
    ) -> tuple[dict, list[ExtractCommand], int]:
        data = dict(seed)
        commands: list[ExtractCommand] = []
        passes = 0
        use_regions = ctx.use_regions and "region_extract" in plan.tools
        use_windows = ctx.use_regions and "prompt_windows" in plan.tools
        if not use_regions and not use_windows:
            return data, commands, passes

        regions, html_by_key = build_region_index(html)
        if "llms_txt" in plan.tools:
            loader = ctx.fetch_llms_txt or fetch_same_origin_llms_txt
            try:
                llms_text = loader(url)
            except Exception:
                llms_text = None
            if llms_text:
                attach_llms_txt_region(regions, html_by_key, llms_text)

        plan_regions = ctx.plan_regions or plan_relevant_regions
        extract = ctx.extract_slices or extract_from_slices
        used_keys: set[str] = set()
        allowed = {region.key for region in regions}
        used_windows = False
        child_prompt = plan.child_prompt

        for _ in range(2):
            if data and not self._incomplete(child_prompt, data, plan):
                break
            keys: list[str] = []
            remaining = {key for key in allowed if key not in used_keys}
            if use_regions and remaining:
                keys = plan_regions(
                    child_prompt,
                    url,
                    compact_region_index([region for region in regions if region.key in remaining]),
                    remaining,
                )
                keys = [key for key in keys if key in remaining]
                if LLMS_REGION_KEY in remaining:
                    keys = [LLMS_REGION_KEY, *[key for key in keys if key != LLMS_REGION_KEY]][:8]
            slices = slice_selected_regions(html_by_key, keys) if keys else []
            if not slices and use_windows and not used_windows:
                slices = slice_prompt_windows(html, child_prompt)
                used_windows = True
            if not slices:
                break
            passes += 1
            used_keys.update(keys)
            slice_keys = keys or [item[0] for item in slices]
            commands.extend(self._region_commands(slice_keys))
            incoming = extract(child_prompt, url, format_slices(slices))
            data = merge_extract_data(data, incoming)

        return data, commands, passes

    def _link_seed(
        self,
        plan: ExtractPlan,
        url: str,
        html: str,
    ) -> tuple[dict, list[ExtractCommand]]:
        if "link_inventory" not in plan.tools:
            return {}, []
        inventory = collect_link_inventory(html, url)
        allowed = plan.constraints.get("allowedDomains")
        allowed_domains = allowed if isinstance(allowed, list) else []
        must_be_outbound = plan.constraints.get("mustBeOutbound") is True
        data = extract_profile_links(
            inventory,
            allowed_domains,
            must_be_outbound=must_be_outbound,
        )
        profiles = data.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            return {}, []
        return data, [
            ExtractCommand(
                name="profiles",
                selector="a[href]",
                attr="href",
                many=True,
            )
        ]

    def extract_page(
        self,
        payload: WebExtractRequest,
        context: WebExtractContext | None = None,
    ) -> WebExtractOutcome:
        ctx = context or WebExtractContext()
        now = ctx.now or (lambda: datetime.now(timezone.utc))
        new_id = ctx.uuid or (lambda: uuid4().hex)
        fetch_html = ctx.fetch_html or fetch_public_html
        plan_commands = ctx.plan_commands or plan_extract_commands
        cache = ctx.cache if ctx.cache is not None else get_cache_service()

        started = now()
        request_id = new_id()
        idempotency_key = self._resolve_idempotency_key(payload)
        cache_key = f"web-extract:extract-page:{idempotency_key}"
        truncated = False
        region_passes = 0
        site_type = ""
        tools_used: list[str] = []
        confidence = 0.0
        check_attempts = 0

        def meta(**overrides) -> WebExtractMeta:
            elapsed = max(int((now() - started).total_seconds() * 1000), 0)
            values = {
                "request_id": request_id,
                "cached": False,
                "idempotency_key": idempotency_key,
                "duration_ms": elapsed,
                "truncated": truncated,
                "region_passes": region_passes,
                "site_type": site_type,
                "tools_used": tools_used,
                "confidence": confidence,
                "check_attempts": check_attempts,
            }
            values.update(overrides)
            return WebExtractMeta(**values)

        cached_result = cache.get_json(cache_key) if cache is not None else None
        if cached_result is not None:
            if isinstance(cached_result, dict) and "result" in cached_result:
                result = WebExtractResult.model_validate(cached_result.get("result"))
                cached_meta = WebExtractMeta.model_validate(cached_result.get("meta") or {})
                cached_confidence = result.confidence or cached_meta.confidence or 1.0
                result = result.model_copy(update={"confidence": cached_confidence})
                return self._build_outcome(
                    status=True,
                    message="Page extracted",
                    status_code=200,
                    result=result,
                    errors=[],
                    meta=cached_meta.model_copy(
                        update={
                            "cached": True,
                            "confidence": cached_confidence,
                            "duration_ms": meta().duration_ms,
                        }
                    ),
                )

            result = WebExtractResult.model_validate(cached_result)
            cached_confidence = result.confidence if result.confidence > 0 else 1.0
            result = result.model_copy(update={"confidence": cached_confidence})
            return self._build_outcome(
                status=True,
                message="Page extracted",
                status_code=200,
                result=result,
                errors=[],
                meta=meta(cached=True, provider="local-html+deepseek", confidence=cached_confidence),
            )

        url = str(payload.url)
        effective_prompt = self._refine_request_prompt(ctx, prompt=payload.prompt, url=url)
        if effective_prompt != payload.prompt.strip():
            tools_used.append("prompt_refiner")
        signals = signals_from_url(url)
        plan = self._resolve_plan(ctx, effective_prompt, signals, allow_llm=False)
        site_type = plan.site_type
        seed, seed_commands, seed_provider = ({}, [], None)
        if "amazon_catalog" in plan.tools:
            seed, seed_commands, seed_provider = self._catalog_seed(ctx, url)
            if seed:
                tools_used.append("amazon_catalog")
        if seed and not self._incomplete(plan.child_prompt, seed, plan):
            verdict = self._score_output(ctx, effective_prompt, url, seed, plan)
            confidence = verdict.confidence
            check_attempts = 1
            if verdict.confidence >= CONFIDENCE_THRESHOLD:
                return self._store_and_succeed(
                    cache=cache,
                    cache_key=cache_key,
                    meta=meta,
                    result=WebExtractResult(
                        url=url,
                        data=seed,
                        commands=seed_commands,
                        confidence=verdict.confidence,
                    ),
                    provider=seed_provider or "amazon-creators",
                )
            previous_check = verdict
        else:
            previous_check = None
        best: tuple[float, dict, list[ExtractCommand], str] | None = (
            (confidence, seed, seed_commands, seed_provider or "amazon-creators")
            if seed and check_attempts
            else None
        )

        try:
            document = fetch_html(url)
            truncated = bool(getattr(document, "truncated", False))
            cleaned_html = sanitize_html(document.html)
            provider = seed_provider or "local-html+deepseek"
            used_browser = False
            browser_fetch = self._resolve_browser_fetch(ctx)

            if looks_like_access_wall(cleaned_html):
                if browser_fetch is None:
                    return self._blocked_outcome(meta)
                try:
                    document = browser_fetch(url)
                    truncated = truncated or bool(getattr(document, "truncated", False))
                    cleaned_html = sanitize_html(document.html)
                    used_browser = True
                    provider = "local-html+playwright"
                    tools_used.append("browser_render")
                except HtmlFetchError:
                    return self._blocked_outcome(meta)
                if looks_like_access_wall(cleaned_html):
                    return self._blocked_outcome(meta, provider="local-html+playwright")

            regions, _html_by_key = build_region_index(cleaned_html)
            signals = PageSignals(
                url=url,
                host=signals.host,
                asin=signals.asin,
                title=page_title(cleaned_html),
                access_wall=looks_like_access_wall(cleaned_html),
                truncated=truncated,
                region_index=compact_region_index(regions)[:4_000],
            )
            plan = self._resolve_plan(ctx, effective_prompt, signals, allow_llm=True)
            site_type = plan.site_type

            if "css_seed" in plan.tools:
                page_seed, page_commands = self._page_seed(cleaned_html, url)
                if page_seed:
                    seed = merge_extract_data(seed, page_seed)
                    seed_commands = self._merge_commands(seed_commands, page_commands)
                    tools_used.append("css_seed")
            if "link_inventory" in plan.tools:
                link_seed, link_commands = self._link_seed(plan, url, cleaned_html)
                if link_seed:
                    seed = merge_extract_data(seed, link_seed)
                    seed_commands = self._merge_commands(seed_commands, link_commands)
                    if "link_inventory" not in tools_used:
                        tools_used.append("link_inventory")

            def take_result(data: dict, commands: list[ExtractCommand], current_provider: str) -> bool:
                nonlocal confidence, check_attempts, previous_check, previous_data, best
                check_attempts += 1
                previous_data = dict(data)
                if not data:
                    previous_check = OutputCheck(confidence=0.0, reason="The extract was empty.")
                    confidence = 0.0
                    return False
                verdict = self._score_output(ctx, effective_prompt, url, data, plan)
                previous_check = verdict
                confidence = verdict.confidence
                if best is None or verdict.confidence >= best[0]:
                    best = (verdict.confidence, data, commands, current_provider)
                return verdict.confidence >= CONFIDENCE_THRESHOLD

            previous_data = dict(seed)
            working_commands = list(seed_commands)
            if seed and not self._incomplete(plan.child_prompt, seed, plan):
                if take_result(seed, seed_commands, provider):
                    return self._store_and_succeed(
                        cache=cache,
                        cache_key=cache_key,
                        meta=meta,
                        result=WebExtractResult(
                            url=url,
                            data=seed,
                            commands=seed_commands,
                            confidence=confidence,
                        ),
                        provider=provider,
                    )

            while check_attempts < MAX_OUTPUT_ATTEMPTS:
                working_data = dict(seed)
                if previous_check is not None and previous_check.confidence < CONFIDENCE_THRESHOLD:
                    working_data = kept_extract(previous_data, previous_check)
                    plan = self._plan_with_retry(plan, previous_check, working_data)
                data = dict(working_data)
                commands = list(working_commands)
                used_chunks = False
                try:
                    chunk_data, chunk_commands = self._extract_from_plain_text(
                        ctx=ctx,
                        plan=plan,
                        url=url,
                        html=cleaned_html,
                        seed=data,
                    )
                    data = chunk_data
                    if chunk_commands:
                        commands = self._merge_commands(commands, chunk_commands)
                        used_chunks = True
                        if "chunk_extract" not in tools_used:
                            tools_used.append("chunk_extract")
                except HTTPException:
                    raise
                except Exception:
                    pass
                try:
                    extracted, region_commands, cycle_passes = self._extract_from_evidence(
                        ctx=ctx,
                        plan=plan,
                        url=url,
                        html=cleaned_html,
                        seed=data,
                    )
                    data = extracted
                    region_passes += cycle_passes
                    if region_commands:
                        commands = [*commands, *region_commands]
                        if "+regions" not in provider:
                            provider = f"{provider}+regions"
                        if "region_extract" in plan.tools and "region_extract" not in tools_used:
                            tools_used.append("region_extract")
                        if "prompt_windows" in plan.tools and "prompt_windows" not in tools_used:
                            tools_used.append("prompt_windows")
                        if "llms_txt" in plan.tools and "llms_txt" not in tools_used:
                            tools_used.append("llms_txt")
                except (CommandPlannerError, ExtractRefineError, HTTPException):
                    pass

                outline = build_dom_outline(cleaned_html)
                regions_complete = bool(data) and not self._incomplete(plan.child_prompt, data, plan)
                retrying = (
                    previous_check is not None
                    and previous_check.confidence < CONFIDENCE_THRESHOLD
                )
                if (
                    "css_commands" in plan.tools
                    and outline.strip()
                    and (not regions_complete or retrying)
                ):
                    planned = plan_commands(plan.child_prompt, url, outline)
                    css_candidates = collect_extract_candidates(cleaned_html, planned)
                    if (
                        browser_fetch is not None
                        and not used_browser
                        and "browser_render" in plan.tools
                        and needs_browser_render(effective_prompt, planned, css_candidates, cleaned_html)
                    ):
                        try:
                            rendered = browser_fetch(url)
                            truncated = truncated or bool(getattr(rendered, "truncated", False))
                            cleaned_html = sanitize_html(rendered.html)
                            used_browser = True
                            provider = "local-html+playwright"
                            if "browser_render" not in tools_used:
                                tools_used.append("browser_render")
                        except HtmlFetchError:
                            rendered = None
                        if rendered is not None:
                            if looks_like_access_wall(cleaned_html):
                                return self._blocked_outcome(meta, provider="local-html+playwright")
                            outline = build_dom_outline(cleaned_html)
                            planned = plan_commands(plan.child_prompt, url, outline)

                    candidates = self._prepare_candidates(cleaned_html, planned)
                    css_data = data_from_candidates(planned, candidates)
                    data = merge_extract_data(data, css_data)
                    if planned:
                        commands = planned
                        if "css_commands" not in tools_used:
                            tools_used.append("css_commands")
                    if ctx.use_refine:
                        refine = ctx.refine_data or refine_extract_data
                        try:
                            refined = refine(plan.child_prompt, url, candidates)
                            if refined:
                                data = merge_extract_data(data, refined)
                                if "+refine" not in provider:
                                    provider = f"{provider}+refine"
                        except ExtractRefineError:
                            pass
                        except HTTPException:
                            pass

                data = self._normalize_data(
                    ctx,
                    prompt=effective_prompt,
                    url=url,
                    plan=plan,
                    data=data,
                )
                if data and "output_normalizer" not in tools_used:
                    tools_used.append("output_normalizer")
                current_provider = provider
                if used_chunks and "+chunks" not in current_provider:
                    current_provider = f"{current_provider}+chunks"

                if take_result(data, commands, current_provider):
                    return self._store_and_succeed(
                        cache=cache,
                        cache_key=cache_key,
                        meta=meta,
                        result=WebExtractResult(
                            url=url,
                            data=data,
                            commands=commands,
                            confidence=confidence,
                        ),
                        provider=current_provider,
                    )
                working_commands = list(commands)

            if best is not None:
                _score, data, commands, provider = best
                confidence = _score
                if confidence < CONFIDENCE_THRESHOLD:
                    return self._low_confidence_outcome(
                        meta,
                        provider,
                        url=url,
                        data=data,
                        commands=commands,
                        confidence=confidence,
                    )
                return self._store_and_succeed(
                    cache=cache,
                    cache_key=cache_key,
                    meta=meta,
                    result=WebExtractResult(
                        url=url,
                        data=data,
                        commands=commands,
                        confidence=confidence,
                    ),
                    provider=provider,
                )

            return self._empty_outcome(
                meta,
                provider,
                commands=seed_commands,
                url=url,
            )
        except HtmlFetchError as exc:
            return self._build_outcome(
                status=False,
                message=exc.message,
                status_code=exc.status_code,
                result=None,
                errors=[
                    WebExtractError(
                        code=exc.code,
                        message=exc.message,
                        retriable=exc.retriable,
                    )
                ],
                meta=meta(provider="local-html"),
            )
        except CommandPlannerError as exc:
            return self._build_outcome(
                status=False,
                message=exc.message,
                status_code=502,
                result=None,
                errors=[
                    WebExtractError(
                        code="PLANNER_FAILED",
                        message=exc.message,
                        retriable=exc.retriable,
                    )
                ],
                meta=meta(),
            )
        except HTTPException:
            raise


web_extract_service = WebExtractService()
