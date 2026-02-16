"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getToken } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        // Check token on mount and route change
        const token = getToken();

        // Public routes that don't need auth
        const publicPaths = ['/login', '/register'];

        if (!token && !publicPaths.includes(pathname)) {
            setAuthorized(false);
            router.push('/login');
        } else {
            setAuthorized(true);
        }
    }, [pathname, router]);

    // Show nothing while checking (or a loading spinner)
    // If we are on a public page, we can render immediately or wait for the check?
    // Ideally, valid token + public page -> redirect to dashboard? Optional.

    // If we are unauthorized and on a protected page, we render nothing until redirect happens.
    if (!authorized && !['/login', '/register'].includes(pathname)) {
        return null;
    }

    return <>{children}</>;
}
