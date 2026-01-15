"use client";

import { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, EngineState } from '../../../lib/api';
import { ProductHeader } from '../../../components/ProductHeader';
import { InsightsPanel } from '../../../components/InsightsPanel';
import { TVChart } from '../../../components/TVChart';
import {
    Box,
    Container,
    Grid,
    GridItem,
    Heading,
    Text,
    VStack,
    HStack,
    Badge,
    Button,
    Icon,
    Spinner,
    Flex,
    useColorModeValue
} from '@chakra-ui/react';
import { ArrowLeft, Activity, TrendingUp, Play } from 'lucide-react';
import { NewsPanel } from '../../../components/NewsPanel';

export default function CoinPage() {
    const router = useRouter();
    const params = useParams();
    // Updated to use params.symbol matching the folder name [symbol]
    const symbol = decodeURIComponent(params.symbol as string);

    const [state, setState] = useState<EngineState | null>(null);
    const [error, setError] = useState('');
    const [chartData, setChartData] = useState<{ time: number; value: number }[]>([]);
    const [mounted, setMounted] = useState(false);

    useEffect(() => { setMounted(true); }, []);

    // 1. Fetch History
    useEffect(() => {
        if (!symbol) return;
        const loadHistory = async () => {
            try {
                const history = await api.getHistory(symbol);
                const sorted = history.sort((a, b) => a.time - b.time);
                setChartData(sorted);
            } catch (e) {
                console.error("Failed to load history", e);
            }
        };
        loadHistory();
    }, [symbol]);

    // 2. Poll Status
    useEffect(() => {
        if (!symbol) return;
        const fetchStatus = async () => {
            try {
                const data = await api.getStatus(symbol);
                if (data) {
                    setState(data);
                    setError('');

                    if (data.insights && data.insights.price) {
                        const now = Math.floor(new Date().getTime() / 1000);
                        const newPoint = { time: now, value: data.insights.price };
                        setChartData(prev => {
                            if (prev.length > 0 && prev[prev.length - 1].time === now) return prev;
                            const newChartParams = [...prev, newPoint].slice(-14400); // 4H window
                            return newChartParams;
                        });
                    }
                }
            } catch (err) {
                console.error("Poll Error:", err);
                setError("ENGINE DISCONNECTED");
                setState(null); // Clear state to trigger Down UI
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 1000);
        return () => clearInterval(interval);
    }, [symbol]);

    const handleStart = async () => {
        if (!symbol) return;
        try {
            await api.startEngine(symbol);
            // Quick status refresh
            const data = await api.getStatus(symbol);
            setState(data);
        } catch (e) {
            console.error("Failed to start engine", e);
            // setError("Failed to start engine"); // Optional: don't block UI if it fails transiently
        }
    };

    if (!mounted) return (
        <Box minH="100vh" bg="black" color="white" display="flex" alignItems="center" justifyContent="center">
            <VStack spacing={4}>
                <Spinner size="xl" color="brand.500" thickness="4px" />
                <Text fontSize="sm" letterSpacing="widest" opacity={0.6}>INITIALIZING ANALYSIS...</Text>
            </VStack>
        </Box>
    );

    if (error) {
        return (
            <Box minH="100vh" bg="black" color="white" display="flex" alignItems="center" justifyContent="center">
                <VStack spacing={4} bg="red.900" p={8} rounded="xl" borderColor="red.700" borderWidth={1}>
                    <Icon as={Activity} boxSize={8} color="red.400" />
                    <Heading size="md" color="red.200">ENGINE SYSTEM OFFLINE</Heading>
                    <Button onClick={() => router.push('/')} colorScheme="whiteAlpha">Return Home</Button>
                </VStack>
            </Box>
        )
    }

    if (!state) {
        return (
            <Box minH="100vh" bg="black" color="white" display="flex" alignItems="center" justifyContent="center">
                <VStack spacing={4}>
                    <Spinner size="xl" color="blue.500" thickness="4px" />
                    <Text fontSize="sm" letterSpacing="widest" opacity={0.6}>INITIALIZING UPLINK...</Text>
                </VStack>
            </Box>
        )
    }

    return (
        <Box minH="100vh" bg="black" color="white" pb={20}>
            <Container maxW="container.xl" pt={6}>

                {/* Nav */}
                <Button
                    variant="ghost"
                    leftIcon={<Icon as={ArrowLeft} />}
                    color="gray.500"
                    _hover={{ color: "white", bg: "whiteAlpha.200" }}
                    onClick={() => router.push('/')}
                    mb={6}
                    size="sm"
                >
                    Select Market
                </Button>

                {/* Header */}
                <Box mb={8} borderBottomWidth={1} borderColor="whiteAlpha.200" pb={6}>
                    <Flex justify="space-between" align="center" wrap="wrap" gap={4}>
                        <VStack align="start" spacing={1}>
                            <HStack>
                                <Heading size="lg" letterSpacing="tight">{state.symbol}</Heading>
                                {state.status === 'STOPPED' && (
                                    <Button
                                        leftIcon={<Icon as={Play} />}
                                        colorScheme="green"
                                        size="sm"
                                        variant="solid"
                                        onClick={handleStart}
                                    >
                                        Start Engine
                                    </Button>
                                )}
                            </HStack>
                            <HStack>
                                <Badge colorScheme={state.status === 'RUNNING' ? 'green' : 'red'}>{state.status}</Badge>
                                <Text fontSize="sm" color="gray.500">PERPETUAL</Text>
                            </HStack>
                        </VStack>
                        <VStack align="end" spacing={1}>
                            <Heading size="lg" fontFamily="mono">${state.insights?.price?.toFixed(2) || '0.00'}</Heading>
                            <Text fontSize="xs" color="gray.500">LAST UPDATE: {new Date().toLocaleTimeString()}</Text>
                        </VStack>
                    </Flex>
                </Box>

                <Grid templateColumns={{ base: "1fr", lg: "3fr 1fr" }} gap={6}>

                    {/* Main Chart */}
                    <GridItem>
                        <Box bg="gray.900" rounded="xl" overflow="hidden" borderWidth={1} borderColor="gray.800">
                            <Flex justify="space-between" p={4} borderBottomWidth={1} borderColor="whiteAlpha.100" bg="whiteAlpha.50">
                                <HStack spacing={4}>
                                    <Button size="xs" colorScheme="blue" variant="solid">1H</Button>
                                    <Button size="xs" variant="ghost" color="gray.500">4H</Button>
                                    <Button size="xs" variant="ghost" color="gray.500">1D</Button>
                                </HStack>
                                <Badge variant="outline" colorScheme="gray">TV_LIGHTWEIGHT_V5</Badge>
                            </Flex>
                            <Box h="500px" w="full" bg="black">
                                <TVChart data={chartData} height={500} />
                            </Box>
                        </Box>
                    </GridItem>

                    {/* Side Stats */}
                    <GridItem>
                        <VStack spacing={6} align="stretch">
                            <Box bg="gray.900" p={6} rounded="xl" borderWidth={1} borderColor="gray.800">
                                <Text fontSize="xs" fontWeight="bold" color="gray.500" mb={4} textTransform="uppercase">Market Regime</Text>
                                <VStack spacing={4}>
                                    <Flex w={16} h={16} rounded="full" bg="purple.900" align="center" justify="center" borderWidth={1} borderColor="purple.700">
                                        <Icon as={Activity} boxSize={8} color="purple.400" />
                                    </Flex>
                                    <Heading size="md">{state.insights?.v3?.regime || 'WAIT'}</Heading>
                                </VStack>
                            </Box>

                            <Box bg="gray.900" p={6} rounded="xl" borderWidth={1} borderColor="gray.800">
                                <Text fontSize="xs" fontWeight="bold" color="gray.500" mb={4} textTransform="uppercase">Active Strategy</Text>
                                <Flex justify="space-between" mb={2}>
                                    <Text color="gray.400" fontSize="sm">Name</Text>
                                    <Text fontFamily="mono" fontWeight="medium">{state.insights?.v3?.active_strategy}</Text>
                                </Flex>
                                <Flex justify="space-between">
                                    <Text color="gray.400" fontSize="sm">Confidence</Text>
                                    <Text color="green.400" fontFamily="mono" fontWeight="bold">
                                        {((state.insights?.v2?.confidence || 0) * 100).toFixed(0)}%
                                    </Text>
                                </Flex>
                            </Box>
                        </VStack>
                    </GridItem>

                </Grid>

                {/* Insights Panel */}
                <Box mt={8}>
                    <Heading size="md" mb={6}>Engine Analysis</Heading>
                    {state.insights && (
                        <div className="tailwind-scope">
                            <InsightsPanel data={state.insights} />
                        </div>
                    )}
                </Box>

                {/* News Section */}
                <Box mt={8}>
                    <NewsPanel symbol={symbol} />
                </Box>

            </Container>
        </Box>
    );
}
