import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
    const token = request.cookies.get('trading_ai_token')?.value
    // Note: We are using localStorage for the actual token in the client app logic (api.ts).
    // However, for Middleware to work on the server side (initial page load protection),
    // we normally need cookies.

    // Since we implemented `auth.ts` using localStorage, the Middleware won't be able to see the token
    // unless we ALSO set a cookie or rely purely on client-side protection.

    // STRATEGY ADJUSTMENT:
    // For this Alpha, we will stick to Client-Side Route Protection in the Shell/Layout 
    // because converting everything to cookies requires Backend changes to set HttpOnly cookies
    // or a more complex auth flow.

    // So for now, this middleware is a pass-through or we can skip it.
    // Actually, let's keep it simple: Client-side check in `src/app/layout.tsx` or a wrapper.

    return NextResponse.next()
}

export const config = {
    matcher: '/:path*',
}
