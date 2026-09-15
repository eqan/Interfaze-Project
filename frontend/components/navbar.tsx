"use client";

import { useState } from "react";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";

import { useAuth } from "@/components/auth-provider";
import { siteConfig } from "@/config/site";
import { Logo } from "@/components/icons";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { signOut, status, user } = useAuth();
  const hasMultipleRoutes = siteConfig.navItems.length > 1;

  function handleSignOut() {
    signOut();
    setIsMenuOpen(false);
    router.replace("/auth");
  }

  function isActivePath(href: string) {
    return href === "/" ? pathname === href : pathname.startsWith(href);
  }

  return (
    <nav className="sticky top-0 z-40 border-b border-[var(--line)] bg-[rgba(248,250,252,0.9)] backdrop-blur">
      <header className="mx-auto flex w-full max-w-6xl items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-4 md:hidden">
          <NextLink className="flex items-center gap-3" href="/">
            <span className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-2 text-accent">
              <Logo size={20} />
            </span>
            <div>
              <p className="text-sm font-semibold text-foreground">
                {siteConfig.name}
              </p>
              <p className="text-sm text-muted">{siteConfig.productTagline}</p>
            </div>
          </NextLink>
        </div>

        <div className="hidden min-w-0 items-center gap-8 md:flex">
          <NextLink className="flex items-center gap-3" href="/">
            <span className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-2 text-accent">
              <Logo size={20} />
            </span>
            <div>
              <p className="text-sm font-semibold text-foreground">{siteConfig.name}</p>
              <p className="text-sm text-muted">{siteConfig.productTagline}</p>
            </div>
          </NextLink>

          {hasMultipleRoutes ? (
            <div className="flex items-center gap-1 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-1">
              {siteConfig.navItems.map((item) => {
                return (
                  <NextLink
                    key={item.href}
                    className={clsx(
                      "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                      isActivePath(item.href)
                        ? "bg-accent text-white shadow-[0_8px_22px_rgba(79,141,247,0.28)]"
                        : "text-muted hover:bg-[var(--surface-strong)] hover:text-foreground",
                    )}
                    href={item.href}
                  >
                    {item.label}
                  </NextLink>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="ml-auto hidden items-center gap-3 md:flex">
          {user ? (
            <>
              <div className="flex items-center gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-3 py-2">
                <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-accent/10 text-sm font-semibold text-foreground">
                  {user.picture ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      alt={user.name}
                      className="h-full w-full object-cover"
                      decoding="async"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      src={user.picture}
                    />
                  ) : (
                    user.name.charAt(0).toUpperCase()
                  )}
                </div>
                <div className="max-w-[12rem]">
                  <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
                  <p className="truncate text-xs text-muted">{user.email}</p>
                </div>
              </div>
              <button
                className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-[var(--surface-strong)]"
                onClick={handleSignOut}
                type="button"
              >
                Sign out
              </button>
            </>
          ) : (
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm text-muted">
              {status === "loading" ? "Restoring session" : "Account unavailable"}
            </div>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2 md:hidden">
          <button
            aria-expanded={isMenuOpen}
            aria-label="Toggle menu"
            className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-2 text-foreground"
            onClick={() => setIsMenuOpen((value) => !value)}
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isMenuOpen ? (
                <path
                  d="M6 18L18 6M6 6l12 12"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
              ) : (
                <path
                  d="M4 6h16M4 12h16M4 18h16"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
              )}
            </svg>
          </button>
        </div>
      </header>

      {isMenuOpen ? (
        <div className="border-t border-[var(--line)] bg-[rgba(248,250,252,0.98)] px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-2">
            {hasMultipleRoutes
              ? siteConfig.navItems.map((item) => {
                  return (
                    <NextLink
                      key={item.href}
                      className={clsx(
                        "rounded-xl px-4 py-3 text-sm transition-colors",
                        isActivePath(item.href)
                          ? "bg-accent text-white"
                          : "border border-[var(--line)] bg-[var(--surface)] text-foreground",
                      )}
                      href={item.href}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      <span className="block font-semibold">{item.label}</span>
                      <span
                        className={clsx(
                          "mt-1 block text-sm",
                          isActivePath(item.href) ? "text-white/85" : "text-muted",
                        )}
                      >
                        {item.description}
                      </span>
                    </NextLink>
                  );
                })
              : null}

            {user ? (
              <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3">
                <p className="text-sm font-medium text-foreground">{user.name}</p>
                <p className="mt-1 text-xs text-muted">{user.email}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm text-muted">
                {status === "loading" ? "Restoring session" : "Account unavailable"}
              </div>
            )}

            {user ? (
              <button
                className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-left text-sm font-semibold text-foreground"
                onClick={handleSignOut}
                type="button"
              >
                Sign out
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </nav>
  );
}
