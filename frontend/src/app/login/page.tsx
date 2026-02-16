"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setToken, setRefreshToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { Lock, User } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append("username", username);
            formData.append("password", password);

            // The backend expects x-www-form-urlencoded or multipart/form-data for OAuth2 password flow
            // But based on routers.py it uses a Pydantic model TokenRequest, which expects JSON body?
            // Let's check routers.py again. 
            // @auth_router.post("/token", response_model=TokenResponse)
            // async def create_token(body: TokenRequest) -> TokenResponse:
            // So it expects JSON.

            const response = await api.post("/auth/token", {
                username,
                password,
            });

            const { access_token, refresh_token } = response.data;
            setToken(access_token);
            setRefreshToken(refresh_token);
            router.push("/");
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Invalid credentials");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -left-[10%] -top-[10%] h-[50%] w-[50%] rounded-full bg-blue-500/10 blur-[120px]" />
                <div className="absolute -bottom-[10%] -right-[10%] h-[50%] w-[50%] rounded-full bg-purple-500/10 blur-[120px]" />
            </div>

            <AcrylicCard className="relative z-10 w-full max-w-sm p-8 shadow-2xl ring-1 ring-white/10 backdrop-blur-3xl">
                <div className="mb-8 flex flex-col items-center">
                    <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
                        <span className="text-xl font-bold text-white">T</span>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">Welcome Back</h1>
                    <p className="text-sm text-muted-foreground">Sign in to your trading terminal</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                        <div className="relative">
                            <User className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
                            <Input
                                type="text"
                                placeholder="Username"
                                className="pl-9 bg-black/5 dark:bg-white/5 border-transparent focus:border-primary/50"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="relative">
                            <Lock className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
                            <Input
                                type="password"
                                placeholder="Password"
                                className="pl-9 bg-black/5 dark:bg-white/5 border-transparent focus:border-primary/50"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    {error && <div className="text-xs text-red-500 font-medium text-center">{error}</div>}

                    <Button
                        type="submit"
                        className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/20 transition-all duration-300 hover:shadow-indigo-500/40"
                        disabled={loading}
                    >
                        {loading ? "Signing in..." : "Sign In"}
                    </Button>
                </form>

                <div className="mt-6 text-center text-xs text-muted-foreground">
                    <p>Demo Credentials: admin / admin</p>
                </div>
            </AcrylicCard>
        </div>
    );
}
