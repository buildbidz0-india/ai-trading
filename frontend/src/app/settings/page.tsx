"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStore } from "@/lib/store";
import { useState, useEffect } from "react";

export default function SettingsPage() {
    const settings = useStore((s) => s.settings);
    const updateSettings = useStore((s) => s.updateSettings);

    // Local state for API keys to avoid saving partial inputs to store/localStorage immediately?
    // Actually, persisting partial input is fine for now as it's local.
    // But typically API keys are sensitive. LocalStorage is not secure.
    // We will just bind them for now.

    // Use local state for notification
    const [saved, setSaved] = useState(false);

    const handleSaveKeys = () => {
        // In a real app, validation or backend sync would happen here.
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    };

    return (
        <Shell>
            <div className="space-y-6 max-w-2xl">
                <h1 className="text-2xl font-bold">Settings</h1>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">API Configuration</h2>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Broker API Key</label>
                        <Input
                            type="password"
                            placeholder="Enter API Key from Broker"
                            className="fluent-input"
                            value={settings.apiKey || ''}
                            onChange={(e) => updateSettings({ apiKey: e.target.value })}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Secret Key</label>
                        <Input
                            type="password"
                            placeholder="Enter Secret Key"
                            className="fluent-input"
                            value={settings.secretKey || ''}
                            onChange={(e) => updateSettings({ secretKey: e.target.value })}
                        />
                    </div>
                    <div className="flex items-center gap-4">
                        <Button onClick={handleSaveKeys}>Save Configuration</Button>
                        {saved && <span className="text-green-500 text-sm animate-pulse">Saved!</span>}
                    </div>
                </AcrylicCard>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">Appearance</h2>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Theme Mode</span>
                        <div className="flex gap-2">
                            <Button
                                variant={settings.theme === 'dark' ? 'default' : 'outline'}
                                size="sm"
                                className={settings.theme === 'dark' ? "bg-primary text-primary-foreground" : ""}
                                onClick={() => updateSettings({ theme: 'dark' })}
                            >
                                Dark
                            </Button>
                            <Button
                                variant={settings.theme === 'light' ? 'default' : 'outline'}
                                size="sm"
                                className={settings.theme === 'light' ? "bg-primary text-primary-foreground" : ""}
                                onClick={() => updateSettings({ theme: 'light' })}
                            >
                                Light
                            </Button>
                        </div>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Reduce Motion</span>
                        <input
                            type="checkbox"
                            className="toggle checkbox"
                            checked={settings.reduceMotion}
                            onChange={(e) => updateSettings({ reduceMotion: e.target.checked })}
                        />
                    </div>
                </AcrylicCard>

                <AcrylicCard className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold border-b border-border pb-2">Trading Preferences</h2>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Default Order Quantity</label>
                        <Input
                            type="number"
                            className="fluent-input"
                            value={settings.defaultQuantity}
                            onChange={(e) => updateSettings({ defaultQuantity: parseInt(e.target.value) || 0 })}
                        />
                    </div>
                </AcrylicCard>
            </div>
        </Shell>
    );
}
