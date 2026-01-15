'use client';

import { Box, keyframes } from '@chakra-ui/react';

const pulse = keyframes`
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.95); }
`;

const glow = keyframes`
  0%, 100% { filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.6)); }
  50% { filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.9)); }
`;

export function AIOSLogo({ size = 48, animate = false }: { size?: number; animate?: boolean }) {
    return (
        <Box
            position="relative"
            width={`${size}px`}
            height={`${size}px`}
            animation={animate ? `${pulse} 2s ease-in-out infinite` : undefined}
        >
            <svg
                width={size}
                height={size}
                viewBox="0 0 100 100"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                style={{
                    animation: animate ? `${glow} 2s ease-in-out infinite` : undefined
                }}
            >
                {/* Outer hexagon */}
                <path
                    d="M50 5 L90 27.5 L90 72.5 L50 95 L10 72.5 L10 27.5 Z"
                    stroke="url(#gradient1)"
                    strokeWidth="3"
                    fill="none"
                />

                {/* Inner AI symbol */}
                <text
                    x="50"
                    y="62"
                    fontSize="42"
                    fontWeight="800"
                    textAnchor="middle"
                    fill="url(#gradient2)"
                    fontFamily="system-ui, -apple-system, sans-serif"
                >
                    AI
                </text>

                {/* Accent dot */}
                <circle
                    cx="50"
                    cy="25"
                    r="4"
                    fill="#10b981"
                >
                    <animate
                        attributeName="opacity"
                        values="0.3;1;0.3"
                        dur="2s"
                        repeatCount="indefinite"
                    />
                </circle>

                <defs>
                    <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#8b5cf6" />
                    </linearGradient>
                    <linearGradient id="gradient2" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#ffffff" />
                        <stop offset="100%" stopColor="#a5b4fc" />
                    </linearGradient>
                </defs>
            </svg>
        </Box>
    );
}
