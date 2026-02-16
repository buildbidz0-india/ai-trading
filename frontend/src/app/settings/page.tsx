"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
    return (
        <Shell>
            <div className="space-y-6 max-w-2xl">
                <h1 className="text-2xl font-bold">Settings</h1>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">API Configuration</h2>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Broker API Key</label>
                        <Input type="password" placeholder="Enter API Key from Broker" className="fluent-input" />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Secret Key</label>
                        <Input type="password" placeholder="Enter Secret Key" className="fluent-input" />
                    </div>
                    <Button>Save Configuration</Button>
                </AcrylicCard>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">Appearance</h2>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Theme Mode</span>
                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" className="bg-primary/10 border-primary">Dark</Button>
                            <Button variant="outline" size="sm">Light</Button>
                        </div>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Reduce Motion</span>
                        <input type="checkbox" className="toggle" />
                    </div>
                </AcrylicCard>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">Trading Preferences</h2>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Default Order Quantity</label>
                        <Input type="number" defaultValue="50" className="fluent-input" />
                    </div>
                </AcrylicCard>
            </div>
        </Shell>
    );
}
