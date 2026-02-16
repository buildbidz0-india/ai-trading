"use client"
import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { AcrylicCard } from "@/components/ui/AcrylicCard"
import {
    LayoutDashboard,
    LineChart,
    Wallet,
    Settings,
    Search,
    Bell,
    Menu
} from "lucide-react"

interface ShellProps {
    children: React.ReactNode
}

import { usePathname } from "next/navigation"

export function Shell({ children }: ShellProps) {
    const [isSidebarOpen, setIsSidebarOpen] = React.useState(true)
    const [isSearchOpen, setIsSearchOpen] = React.useState(false)
    const [isNotificationsOpen, setIsNotificationsOpen] = React.useState(false)
    const pathname = usePathname()

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background relative">
            {/* Search Overlay */}
            {isSearchOpen && (
                <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-start justify-center pt-24" onClick={() => setIsSearchOpen(false)}>
                    <div className="w-full max-w-lg p-4" onClick={e => e.stopPropagation()}>
                        <AcrylicCard className="p-4 flex gap-2 items-center ring-1 ring-primary/20 shadow-2xl">
                            <Search className="size-5 text-muted-foreground" />
                            <input autoFocus placeholder="Search tickers, orders, or settings..." className="flex-1 bg-transparent outline-none text-lg placeholder:text-muted-foreground/50" />
                            <div className="text-xs text-muted-foreground border border-border px-1.5 py-0.5 rounded kbd">ESC</div>
                        </AcrylicCard>
                    </div>
                </div>
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "mica-material z-20 hidden md:flex h-full flex-col border-r transition-all duration-300",
                    isSidebarOpen ? "w-64" : "w-16"
                )}
            >
                <div className="flex h-16 items-center border-b border-white/5 px-4 backdrop-blur-md">
                    <div className={cn("flex items-center gap-2 font-semibold transition-all duration-300", !isSidebarOpen && "justify-center w-full")}>
                        <div className="size-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg flex items-center justify-center text-white font-bold">
                            T
                        </div>
                        {isSidebarOpen && <span className="text-lg bg-clip-text text-transparent bg-gradient-to-r from-foreground to-muted-foreground font-tracking-tight">TradingAI</span>}
                    </div>
                </div>

                <nav className="flex-1 space-y-2 p-2 relative">
                    <NavItem href="/" icon={LayoutDashboard} label="Dashboard" isOpen={isSidebarOpen} active={pathname === "/"} />
                    <NavItem href="/charts" icon={LineChart} label="Market" isOpen={isSidebarOpen} active={pathname === "/charts"} />
                    <NavItem href="/wallet" icon={Wallet} label="Portfolio" isOpen={isSidebarOpen} active={pathname === "/wallet"} />
                    <div className="my-2 border-t border-white/5 mx-2" />
                    <NavItem href="/settings" icon={Settings} label="Settings" isOpen={isSidebarOpen} active={pathname === "/settings"} />
                </nav>

                <div className="p-2 border-t border-white/5">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="w-full justify-center opacity-70 hover:opacity-100"
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    >
                        <Menu className="size-4" />
                    </Button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col min-w-0 relative">
                {/* Header */}
                <header className="mica-material h-16 border-b flex items-center justify-between px-6 z-10 sticky top-0">
                    <div className="text-sm text-muted-foreground font-medium flex items-center gap-2">
                        <span className={cn("w-2 h-2 rounded-full", "bg-green-500 animate-pulse")} />
                        NIFTY 50 • <span className="text-green-500 font-mono">22,145.00 (+0.4%)</span>
                    </div>

                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground" onClick={() => setIsSearchOpen(true)}>
                            <Search className="size-4" />
                        </Button>

                        <div className="relative">
                            <Button variant="ghost" size="icon" className={cn("text-muted-foreground hover:text-foreground transition-colors", isNotificationsOpen && "text-foreground bg-accent")} onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}>
                                <Bell className="size-4" />
                                <span className="absolute top-2.5 right-2.5 size-1.5 bg-red-500 rounded-full ring-2 ring-background" />
                            </Button>

                            {isNotificationsOpen && (
                                <div className="absolute right-0 top-12 w-80 z-50 animate-in slide-in-from-top-2 fade-in duration-200">
                                    <AcrylicCard className="p-0 overflow-hidden shadow-2xl ring-1 ring-border/50">
                                        <div className="p-3 border-b border-border bg-muted/40 font-semibold text-xs uppercase tracking-wider text-muted-foreground">Notifications</div>
                                        <div className="max-h-64 overflow-y-auto">
                                            <div className="p-3 border-b border-border/50 hover:bg-muted/50 cursor-pointer transition-colors">
                                                <div className="flex justify-between items-start mb-1">
                                                    <div className="text-xs font-bold text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded">ORDER FILLED</div>
                                                    <div className="text-[10px] text-muted-foreground">2m ago</div>
                                                </div>
                                                <div className="text-sm">Bought 50 NIFTY @ 22,150</div>
                                            </div>
                                            <div className="p-3 border-b border-border/50 hover:bg-muted/50 cursor-pointer transition-colors">
                                                <div className="flex justify-between items-start mb-1">
                                                    <div className="text-xs font-bold text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded">SYSTEM</div>
                                                    <div className="text-[10px] text-muted-foreground">1h ago</div>
                                                </div>
                                                <div className="text-sm">Market latency optimized (12ms)</div>
                                            </div>
                                        </div>
                                        <div className="p-2 text-center text-xs text-muted-foreground hover:text-foreground cursor-pointer border-t border-border/50 bg-muted/20">
                                            View all notifications
                                        </div>
                                    </AcrylicCard>
                                </div>
                            )}
                        </div>

                        <div className="size-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 ring-2 ring-background cursor-pointer hover:ring-primary/50 transition-all" />
                    </div>
                </header>

                {/* content */}
                <div className="flex-1 overflow-auto p-4 md:p-6 lg:p-8 space-y-6">
                    {children}
                </div>
            </main>
        </div>
    )
}

import Link from "next/link"

function NavItem({ icon: Icon, label, isOpen, active, href }: { icon: any, label: string, isOpen: boolean, active?: boolean, href: string }) {
    if (!isOpen) {
        return (
            <Link href={href} className="block mb-1" title={label}>
                <div
                    className={cn(
                        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 size-9 hover:bg-accent hover:text-accent-foreground border bg-background shadow-xs w-full",
                        active ? "bg-secondary text-secondary-foreground shadow-md bg-white/5" : "hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50"
                    )}
                >
                    <Icon className={cn("size-5", active ? "text-primary" : "text-muted-foreground")} />
                </div>
            </Link>
        )
    }

    return (
        <Link href={href} className="block mb-1">
            <div
                className={cn(
                    "inline-flex items-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 h-9 px-4 py-2 hover:bg-accent hover:text-accent-foreground w-full justify-start",
                    active ? "bg-secondary text-secondary-foreground shadow-sm bg-white/5 border border-white/5" : "hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50"
                )}
            >
                <Icon className={cn("size-4", active ? "text-primary" : "text-muted-foreground")} />
                <span className={active ? "font-medium" : "font-normal text-muted-foreground"}>{label}</span>
            </div>
        </Link>
    )
}
