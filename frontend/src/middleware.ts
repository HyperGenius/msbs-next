import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const PUBLIC_ROUTES = [
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/signup(.*)',
  '/onboarding(.*)',
]
// 開発用ページ（/dev/sim など）。本番ではページと Route Handler 自身も 404 を返す。
const DEV_ONLY_PUBLIC_ROUTES = ['/dev(.*)', '/api/dev(.*)']

const isPublicRoute = createRouteMatcher(
  process.env.NODE_ENV === 'development'
    ? [...PUBLIC_ROUTES, ...DEV_ONLY_PUBLIC_ROUTES]
    : PUBLIC_ROUTES
)

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) await auth.protect()
})

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
