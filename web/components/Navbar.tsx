'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import { User } from '@supabase/supabase-js'
import { LogOut, User as UserIcon } from 'lucide-react'

export default function Navbar() {
    const [user, setUser] = useState<User | null>(null)

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null)
        })

        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null)
        })

        return () => subscription.unsubscribe()
    }, [])

    return (
        <nav className="border-b border-gray-800 bg-black/50 backdrop-blur-md sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center">
                        <Link href="/" className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                            AI Trader Command
                        </Link>
                    </div>
                    <div className="flex items-center gap-4">
                        {user ? (
                            <>
                                <div className="flex items-center gap-2 text-sm text-gray-400">
                                    <UserIcon size={16} />
                                    <span>{user.email}</span>
                                </div>
                                <button
                                    onClick={() => supabase.auth.signOut()}
                                    className="p-2 text-gray-400 hover:text-white transition-colors"
                                    title="Sign Out"
                                >
                                    <LogOut size={18} />
                                </button>
                            </>
                        ) : (
                            <Link
                                href="/login"
                                className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
                            >
                                Sign In
                            </Link>
                        )}
                    </div>
                </div>
            </div>
        </nav>
    )
}
