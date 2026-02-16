"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getToken } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [state, setState] = useState<'loading' | 'authorized' | 'redirecting'>('loading');

    const publicPaths = ['/login', '/register'];

    useEffect(() => {
        const token = getToken();

        if (!token && !publicPaths.includes(pathname)) {
            setState('redirecting');
            router.push('/login');
        } else {
            setState('authorized');
        }
    }, [pathname, router]);

    if (state === 'loading' || state === 'redirecting') {
        if (publicPaths.includes(pathname)) {
            return <>{children}</>;
        }

        return (
            <div className="flex h-screen w-full items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    {/* Animated logo */}
                    <div className="relative">
                        <div className="size-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg flex items-center justify-center text-white font-bold text-xl animate-pulse">
                            T
                        </div>
                        <div className="absolute -inset-2 rounded-2xl border-2 border-indigo-500/20 animate-ping" />
                    </div>
                    <div className="text-sm text-muted-foreground animate-pulse">
                        {state === 'redirecting' ? 'Redirecting to login...' : 'Loading...'}
                    </div>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
