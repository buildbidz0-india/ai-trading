import { cn } from "@/lib/utils"

interface AcrylicCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode
    variant?: "default" | "mica" | "solid"
}

export function AcrylicCard({
    children,
    className,
    variant = "default",
    ...props
}: AcrylicCardProps) {
    return (
        <div
            className={cn(
                "rounded-xl border shadow-sm transition-all duration-300",
                {
                    "acrylic-material": variant === "default",
                    "mica-material": variant === "mica",
                    "bg-card text-card-foreground border-border": variant === "solid"
                },
                className
            )}
            {...props}
        >
            {children}
        </div>
    )
}
