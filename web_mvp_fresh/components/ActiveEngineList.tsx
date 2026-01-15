import { useEffect, useState } from 'react';
import { Box, SimpleGrid, Text, Badge, HStack, VStack, Flex, Heading, Icon, Button } from '@chakra-ui/react';
import { api, EngineState } from '../lib/api';
import { Activity, Zap, BarChart2, Shield, TrendingUp, Play } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { SkeletonEngineGrid } from './SkeletonCard';

export function ActiveEngineList() {
    const router = useRouter();
    const [coins, setCoins] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const res = await api.getCoins();
                // We want to show active engines. If active list is empty, maybe fallback to defaults?
                // But CLI only shows what's running. Let's show active.
                if (res.active && res.active.length > 0) {
                    setCoins(res.active);
                } else {
                    // Fallback to defaults if nothing running, so UI isn't empty?
                    // The prompt "Make sure all engeines are returning data" implies we want to see data.
                    // If nothing is running, we can't show data. 
                    // Let's rely on user starting them or CLI running them.
                    setCoins(res.active || []);
                }
            } catch (e) {
                console.error("Failed to fetch coins", e);
            } finally {
                setLoading(false);
            }
        };
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading) return <SkeletonEngineGrid />;

    if (coins.length === 0) {
        return (
            <Box
                textAlign="center"
                py={20}
                bg="whiteAlpha.50"
                rounded="2xl"
                borderStyle="dashed"
                borderWidth={2}
                borderColor="whiteAlpha.200"
            >
                <VStack spacing={4}>
                    <Icon as={Activity} boxSize={12} color="gray.600" />
                    <Heading size="md" color="gray.400">No Active Engines</Heading>
                    <Text color="gray.600" maxW="sm" fontSize="sm">
                        Start analyzing a symbol above or run engines via CLI to see real-time data
                    </Text>
                    <Button
                        colorScheme="brand"
                        size="sm"
                        leftIcon={<Icon as={Play} />}
                        onClick={() => router.push('/')}
                    >
                        Analyze Symbol
                    </Button>
                </VStack>
            </Box>
        );
    }

    return (
        <Box w="full">
            <Text fontSize="xl" fontWeight="bold" mb={4} color="gray.300">Live Engine Monitor</Text>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} spacing={4} w="full">
                {coins.map(c => <EngineCard key={c} symbol={c} />)}
            </SimpleGrid>
        </Box>
    );
}

function EngineCard({ symbol }: { symbol: string }) {
    const router = useRouter();
    const [state, setState] = useState<EngineState | null>(null);
    const [isHovered, setIsHovered] = useState(false);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await api.getStatus(symbol);
                setState(data);
            } catch (e) { console.error(e); }
        };
        load();
        // Poll at 1s interval for live "CLI-like" feel
        const interval = setInterval(load, 1000);
        return () => clearInterval(interval);
    }, [symbol]);

    // Handle click to go to detail
    const handleClick = () => {
        const slug = encodeURIComponent(symbol);
        router.push(`/coin/${slug}`);
    };

    if (!state) {
        return (
            <Box p={5} bg="gray.900" rounded="xl" borderWidth={1} borderColor="whiteAlpha.100" h="200px">
                <Flex justify="space-between" mb={3}>
                    <Box height="20px" width="100px" bg="whiteAlpha.100" rounded="md" />
                    <Box height="16px" width="60px" bg="whiteAlpha.100" rounded="full" />
                </Flex>
                <Box height="32px" width="120px" bg="whiteAlpha.100" rounded="md" mb={4} />
                <SimpleGrid columns={2} spacing={3}>
                    <Box height="60px" bg="whiteAlpha.100" rounded="lg" />
                    <Box height="60px" bg="whiteAlpha.100" rounded="lg" />
                    <Box height="60px" bg="whiteAlpha.100" rounded="lg" />
                    <Box height="60px" bg="whiteAlpha.100" rounded="lg" />
                </SimpleGrid>
            </Box>
        );
    }

    const i = state.insights;
    const isRunning = state.status === 'RUNNING';

    return (
        <Box
            p={5}
            bg="gray.900"
            rounded="xl"
            borderWidth={1}
            borderColor="whiteAlpha.100"
            cursor="pointer"
            position="relative"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={handleClick}
            _hover={{
                borderColor: 'brand.400',
                transform: 'translateY(-4px) scale(1.01)',
                boxShadow: '0 12px 28px rgba(99, 102, 241, 0.15)'
            }}
            transition="all 0.25s cubic-bezier(0.4, 0, 0.2, 1)"
        >
            <Flex justify="space-between" mb={3} align="center">
                <HStack>
                    <Text fontWeight="bold" fontSize="lg">{symbol}</Text>
                </HStack>
                <Badge
                    colorScheme={isRunning ? 'green' : 'red'}
                    variant={isRunning ? 'solid' : 'subtle'}
                    fontSize="0.6em"
                    px={2}
                    rounded="full"
                >
                    {state.status}
                </Badge>
            </Flex>

            <Text fontSize="2xl" fontWeight="mono" mb={4} color="white">
                ${i?.price?.toFixed(2) || '---'}
            </Text>

            <SimpleGrid columns={2} spacing={3}>
                {/* V1 Legacy */}
                <Box bg="whiteAlpha.50" p={2} rounded="lg">
                    <HStack color="yellow.400" mb={1} justify="space-between">
                        <HStack spacing={1}>
                            <Zap size={12} />
                            <Text fontSize="xs" fontWeight="bold">V1</Text>
                        </HStack>
                        <Text fontSize="xs" color="whiteAlpha.600">{i?.v1?.velocity?.toFixed(2)}%</Text>
                    </HStack>
                    <Text fontWeight="bold" fontSize="sm" color="yellow.100">{i?.v1?.state || 'WAIT'}</Text>
                </Box>

                {/* V3 Strict */}
                <Box bg="whiteAlpha.50" p={2} rounded="lg">
                    <HStack color="purple.400" mb={1} justify="space-between">
                        <HStack spacing={1}>
                            <BarChart2 size={12} />
                            <Text fontSize="xs" fontWeight="bold">V3</Text>
                        </HStack>
                    </HStack>
                    <Text fontWeight="bold" fontSize="sm" color="purple.100">{i?.v3?.state || 'WAIT'}</Text>
                </Box>

                {/* V2 Sentiment */}
                <Box bg="whiteAlpha.50" p={2} rounded="lg">
                    <HStack color="blue.400" mb={1} justify="space-between">
                        <HStack spacing={1}>
                            <TrendingUp size={12} />
                            <Text fontSize="xs" fontWeight="bold">V2</Text>
                        </HStack>
                        <Text fontSize="xs" color="whiteAlpha.600">{((i?.v2?.confidence || 0) * 100).toFixed(0)}%</Text>
                    </HStack>
                    <Text fontWeight="bold" fontSize="sm" color="blue.100">{i?.v2?.signal || 'NEUTRAL'}</Text>
                </Box>

                {/* V4 AI */}
                <Box bg="whiteAlpha.50" p={2} rounded="lg">
                    <HStack color="emerald.400" mb={1} justify="space-between">
                        <HStack spacing={1}>
                            <Shield size={12} />
                            <Text fontSize="xs" fontWeight="bold">V4</Text>
                        </HStack>
                        <Text fontSize="xs" color="whiteAlpha.600">{i?.v4?.risk_score?.toFixed(1)}</Text>
                    </HStack>
                    <Text fontWeight="bold" fontSize="sm" color="emerald.100">{i?.v4?.signal || 'ACTIVE'}</Text>
                </Box>
            </SimpleGrid>

            {isHovered && (
                <Text position="absolute" bottom={2} right={3} fontSize="xs" color="brand.400" fontWeight="bold">
                    VIEW ANALYSIS &rarr;
                </Text>
            )}
        </Box>
    );
}
