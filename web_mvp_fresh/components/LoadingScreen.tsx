'use client';

import { Box, VStack, HStack, Text, keyframes, Flex, Icon } from '@chakra-ui/react';
import { Zap, TrendingUp, BarChart2, Shield } from 'lucide-react';
import { AIOSLogo } from './AIOSLogo';

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

export function LoadingScreen({ message = "Initializing Engines..." }: { message?: string }) {
    return (
        <Box
            position="fixed"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="black"
            display="flex"
            alignItems="center"
            justifyContent="center"
            zIndex={9999}
        >
            <VStack spacing={8} animation={`${fadeIn} 0.5s ease-out`}>
                <AIOSLogo size={80} animate={true} />

                <VStack spacing={3}>
                    <Text
                        fontSize="2xl"
                        fontWeight="bold"
                        bgGradient="linear(to-r, brand.400, purple.400)"
                        bgClip="text"
                    >
                        AIOS
                    </Text>
                    <Text color="gray.500" fontSize="sm" letterSpacing="wider">
                        {message.toUpperCase()}
                    </Text>
                </VStack>

                {/* Engine Status Indicators */}
                <HStack spacing={4} pt={4}>
                    {[
                        { icon: Zap, label: 'V1', color: 'yellow.400' },
                        { icon: TrendingUp, label: 'V2', color: 'blue.400' },
                        { icon: BarChart2, label: 'V3', color: 'purple.400' },
                        { icon: Shield, label: 'V4', color: 'emerald.400' }
                    ].map((engine, idx) => (
                        <VStack
                            key={idx}
                            spacing={1}
                            opacity={0.6}
                            animation={`${pulse} 1.5s ease-in-out infinite`}
                            style={{ animationDelay: `${idx * 0.2}s` }}
                        >
                            <Icon as={engine.icon} boxSize={5} color={engine.color} />
                            <Text fontSize="xs" color="gray.600">{engine.label}</Text>
                        </VStack>
                    ))}
                </HStack>

                {/* Progress indicator */}
                <Box
                    w="200px"
                    h="1px"
                    bg="gray.800"
                    overflow="hidden"
                    rounded="full"
                >
                    <Box
                        h="full"
                        w="full"
                        bgGradient="linear(to-r, transparent, brand.500, transparent)"
                        bgSize="200% 100%"
                        animation={`${shimmer} 1.5s ease-in-out infinite`}
                    />
                </Box>
            </VStack>
        </Box>
    );
}

export function EngineLoadingCard() {
    return (
        <Box
            p={5}
            bg="gray.900"
            rounded="xl"
            borderWidth={1}
            borderColor="whiteAlpha.100"
            h="200px"
            position="relative"
            overflow="hidden"
        >
            {/* Shimmer overlay */}
            <Box
                position="absolute"
                top={0}
                left={0}
                right={0}
                bottom={0}
                bgGradient="linear(to-r, transparent, whiteAlpha.100, transparent)"
                bgSize="200% 100%"
                animation={`${shimmer} 2s ease-in-out infinite`}
            />

            {/* Content skeleton */}
            <Flex justify="space-between" mb={3}>
                <Box height="20px" width="100px" bg="whiteAlpha.100" rounded="md" />
                <Box height="16px" width="60px" bg="whiteAlpha.100" rounded="full" />
            </Flex>
            <Box height="32px" width="120px" bg="whiteAlpha.100" rounded="md" mb={4} />
            <VStack spacing={3} align="stretch">
                {[1, 2].map(i => (
                    <Flex key={i} gap={3}>
                        <Box flex={1} height="60px" bg="whiteAlpha.100" rounded="lg" />
                        <Box flex={1} height="60px" bg="whiteAlpha.100" rounded="lg" />
                    </Flex>
                ))}
            </VStack>
        </Box>
    );
}
