"use client"
import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
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

export function Shell({ children }: ShellProps) {
    const [isSidebarOpen, setIsSidebarOpen] = React.useState(true)

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background">
            {/* Sidebar */}
            <aside
                className={cn(
                    "mica-material z-20 hidden md:flex h-full flex-col border-r transition-all duration-300",
                    isSidebarOpen ? "w-64" : "w-16"
                )}
            >
                <div className="flex h-16 items-center border-b border-white/5 px-4 backdrop-blur-md">
                    <div className={cn("flex items-center gap-2 font-semibold", !isSidebarOpen && "justify-center w-full")}>
                        <div className="size-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg" />
                        {isSidebarOpen && <span className="text-lg bg-clip-text text-transparent bg-gradient-to-r from-foreground to-muted-foreground">TradeAI</span>}
                    </div>
                </div>

                <nav className="flex-1 space-y-2 p-2 relative">
                    <NavItem icon={LayoutDashboard} label="Dashboard" isOpen={isSidebarOpen} active />
                    <NavItem icon={LineChart} label="Market" isOpen={isSidebarOpen} />
                    <NavItem icon={Wallet} label="Portfolio" isOpen={isSidebarOpen} />
                    <div className="my-2 border-t border-white/5 mx-2" />
                    <NavItem icon={Settings} label="Settings" isOpen={isSidebarOpen} />
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
                    <div className="text-sm text-muted-foreground font-medium">NIFTY 50 • <span className="text-green-500">22,145.00 (+0.4%)</span></div>

                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" className="text-muted-foreground">
                            <Search className="size-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="text-muted-foreground">
                            <Bell className="size-4" />
                        </Button>
                        <div className="size-8 rounded-full bg-gradient-to-r from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 border ring-1 ring-white/10" />
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

function NavItem({ icon: Icon, label, isOpen, active }: { icon: any, label: string, isOpen: boolean, active?: boolean }) {
    if (!isOpen) {
        return (
            <Button
                variant={active ? "secondary" : "ghost"}
                size="icon"
                className={cn("w-full mb-1", active && "shadow-md bg-white/5")}
                title={label}
            >
                <Icon className={cn("size-5", active ? "text-primary" : "text-muted-foreground")} />
            </Button>
        )
    }

    return (
        <Button
            variant={active ? "secondary" : "ghost"}
            className={cn("w-full justify-start gap-3 mb-1", active && "shadow-sm bg-white/5 border border-white/5")}
        >
            <Icon className={cn("size-4", active ? "text-primary" : "text-muted-foreground")} />
            <span className={active ? "font-medium" : "font-normal text-muted-foreground"}>{label}</span>
        </Button>
    )
}
