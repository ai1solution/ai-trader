import { EngineInsights } from '../lib/api';
import {
    Box,
    SimpleGrid,
    Text,
    HStack,
    VStack,
    Icon,
    Flex,
    Badge,
    Progress,
    useColorModeValue
} from '@chakra-ui/react';
import { Zap, TrendingUp, BarChart2, Shield, Activity, ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface Props {
    data: EngineInsights;
}

export function InsightsPanel({ data }: Props) {
    // Calculate consensus
    const signals = [
        (data.v1?.velocity || 0) > 0.1 ? 1 : (data.v1?.velocity || 0) < -0.1 ? -1 : 0,
        data.v2?.signal === 'BUY' ? 1 : data.v2?.signal === 'SELL' ? -1 : 0,
        0,
        data.v4?.signal === 'BUY' ? 1 : data.v4?.signal === 'SELL' ? -1 : 0
    ];
    const score = signals.reduce((a, b) => a + b, 0);

    let sentiment = { text: "NEUTRAL", color: "gray.400", borderColor: "gray.800", bg: "gray.900" };
    if (score >= 2) sentiment = { text: "STRONG BULLISH", color: "green.400", borderColor: "green.500", bg: "green.900" };
    else if (score === 1) sentiment = { text: "LEANING BULLISH", color: "green.300", borderColor: "green.500", bg: "green.900" };
    else if (score === -1) sentiment = { text: "LEANING BEARISH", color: "red.300", borderColor: "red.500", bg: "red.900" };
    else if (score <= -2) sentiment = { text: "STRONG BEARISH", color: "red.400", borderColor: "red.500", bg: "red.900" };

    return (
        <VStack spacing={6} w="full" align="stretch">

            {/* Market Consensus Banner */}
            <Box
                p={6}
                rounded="2xl"
                bg="gray.900"
                borderWidth={1}
                borderColor={sentiment.borderColor}
                boxShadow="xl"
            >
                <Flex direction={{ base: "column", md: "row" }} justify="space-between" align="center" gap={6}>
                    <HStack spacing={4}>
                        <Flex p={4} rounded="xl" bg="whiteAlpha.100" color={sentiment.color}>
                            <Icon as={Activity} boxSize={8} />
                        </Flex>
                        <Box>
                            <Text fontSize="sm" fontWeight="bold" color="gray.500" letterSpacing="wide" textTransform="uppercase">Market Consensus</Text>
                            <Text fontSize="3xl" fontWeight="black" color={sentiment.color} lineHeight="shorter">
                                {sentiment.text}
                            </Text>
                        </Box>
                    </HStack>

                    <Flex gap={12} textAlign="center">
                        <Box>
                            <Text fontSize="xs" color="gray.500" textTransform="uppercase" mb={1}>Agreement</Text>
                            <Text fontFamily="mono" fontSize="2xl" fontWeight="bold" color="white">
                                {(Math.abs(score) / 4 * 100).toFixed(0)}%
                            </Text>
                        </Box>
                        <Box>
                            <Text fontSize="xs" color="gray.500" textTransform="uppercase" mb={1}>Active Engines</Text>
                            <Text fontFamily="mono" fontSize="2xl" fontWeight="bold" color="white">4/4</Text>
                        </Box>
                    </Flex>
                </Flex>
            </Box>

            {/* Engine Grid */}
            <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing={6}>

                {/* V1 LEGACY */}
                <EngineCard
                    title="V1 Legacy"
                    subtitle="Momentum Engine"
                    icon={Zap}
                    color="yellow.400"
                    borderColor="yellow.900"
                >
                    <VStack spacing={4} align="stretch" pt={2}>
                        <Flex justify="space-between" align="center">
                            <Text color="gray.500" fontSize="sm">Action State</Text>
                            <StateBadge state={data.v1?.state} />
                        </Flex>

                        <Box>
                            <Flex justify="space-between" fontSize="sm" mb={2}>
                                <Text color="gray.500">Velocity</Text>
                                <Text fontFamily="mono" fontWeight="bold" color={(data.v1?.velocity || 0) > 0 ? "green.400" : "red.400"}>
                                    {data.v1?.velocity?.toFixed(2) || '0.00'}%
                                </Text>
                            </Flex>
                            <Progress
                                value={Math.abs((data.v1?.velocity || 0) * 100)}
                                colorScheme={(data.v1?.velocity || 0) > 0 ? "green" : "red"}
                                size="xs"
                                rounded="full"
                                bg="whiteAlpha.100"
                            />
                        </Box>

                        <Flex justify="space-between" align="center" pt={2} borderTopWidth={1} borderColor="whiteAlpha.100">
                            <Text color="gray.500" fontSize="sm">Trend</Text>
                            <TrendBadge direction={data.v1?.trend} />
                        </Flex>
                    </VStack>
                </EngineCard>

                {/* V2 MODERN */}
                <EngineCard
                    title="V2 Modern"
                    subtitle="Probabilistic Engine"
                    icon={TrendingUp}
                    color="blue.400"
                    borderColor="blue.900"
                >
                    <VStack spacing={4} align="stretch" pt={2}>
                        <Flex justify="space-between" align="center">
                            <Text color="gray.500" fontSize="sm">Signal</Text>
                            <SignalBadge signal={data.v2?.signal} />
                        </Flex>

                        <Box>
                            <Flex justify="space-between" fontSize="sm" mb={2}>
                                <Text color="gray.500">Confidence</Text>
                                <Text fontFamily="mono" fontWeight="bold" color="gray.300">
                                    {data.v2?.confidence ? `${(data.v2.confidence * 100).toFixed(0)}%` : '--'}
                                </Text>
                            </Flex>
                            <Progress
                                value={(data.v2?.confidence || 0) * 100}
                                colorScheme="blue"
                                size="xs"
                                rounded="full"
                                bg="whiteAlpha.100"
                            />
                        </Box>
                    </VStack>
                </EngineCard>

                {/* V3 STRICT */}
                <EngineCard
                    title="V3 Strict"
                    subtitle="State Machine"
                    icon={BarChart2}
                    color="purple.400"
                    borderColor="purple.900"
                >
                    <VStack spacing={4} align="stretch" pt={2}>
                        <Flex justify="space-between" align="center">
                            <Text color="gray.500" fontSize="sm">Machine State</Text>
                            <StateBadge state={data.v3?.state} colorScheme="purple" />
                        </Flex>

                        <Box p={3} bg="whiteAlpha.50" rounded="lg" borderWidth={1} borderColor="whiteAlpha.100">
                            <Text fontSize="xs" fontWeight="bold" color="gray.500" textTransform="uppercase" mb={1}>Regime</Text>
                            <Text fontWeight="bold" color="purple.300">{data.v3?.regime || 'DETECTING'}</Text>
                        </Box>

                        <Flex justify="space-between" align="center">
                            <Text color="gray.500" fontSize="sm">Strategy</Text>
                            <Badge variant="subtle" colorScheme="gray">{data.v3?.active_strategy}</Badge>
                        </Flex>
                    </VStack>
                </EngineCard>

                {/* V4 CAPITAL */}
                <EngineCard
                    title="V4 Capital"
                    subtitle="Risk & Portfolio"
                    icon={Shield}
                    color="emerald.400"
                    borderColor="emerald.900"
                >
                    <VStack spacing={4} align="stretch" pt={2}>
                        <Flex justify="space-between" align="center">
                            <Text color="gray.500" fontSize="sm">Status</Text>
                            <Badge colorScheme="emerald" variant="outline" px={2} rounded="full">
                                {data.v4?.signal || 'ACTIVE'}
                            </Badge>
                        </Flex>

                        <Box>
                            <Flex justify="space-between" fontSize="sm" mb={2}>
                                <Text color="gray.500">Risk Score</Text>
                                <Text fontFamily="mono" fontWeight="bold" color="gray.300">
                                    {data.v4?.risk_score?.toFixed(2)}
                                </Text>
                            </Flex>
                            <Progress
                                value={(data.v4?.risk_score || 0) * 100}
                                colorScheme={(data.v4?.risk_score || 0) > 0.5 ? "yellow" : "emerald"}
                                size="xs"
                                rounded="full"
                                bg="whiteAlpha.100"
                            />
                        </Box>

                        <Box pt={2} borderTopWidth={1} borderColor="whiteAlpha.100">
                            <Text fontSize="xs" color="gray.500" textTransform="uppercase">Est. PnL Projection</Text>
                            <Text fontSize="xl" fontFamily="mono" fontWeight="bold" color="white" mt={1}>
                                ${data.v4?.pnl_projected?.toFixed(2) || '0.00'}
                            </Text>
                        </Box>
                    </VStack>
                </EngineCard>

            </SimpleGrid>
        </VStack>
    );
}

function EngineCard({ title, subtitle, icon, children, color, borderColor }: any) {
    return (
        <Box
            p={6}
            bg="gray.900"
            rounded="2xl"
            borderWidth={1}
            borderColor={borderColor || "gray.800"}
            position="relative"
            overflow="hidden"
            _hover={{ borderColor: color, transform: 'translateY(-4px)', boxShadow: 'xl' }}
            transition="all 0.25s cubic-bezier(0.4, 0, 0.2, 1)"
        >
            <Flex justify="space-between" align="start" mb={6}>
                <Box>
                    <Text fontWeight="bold" fontSize="lg" color={color}>{title}</Text>
                    <Text fontSize="xs" fontWeight="bold" color="gray.500" textTransform="uppercase" letterSpacing="wide">{subtitle}</Text>
                </Box>
                <Flex p={2} bg="whiteAlpha.100" rounded="lg" color={color}>
                    <Icon as={icon} boxSize={5} />
                </Flex>
            </Flex>
            {children}
        </Box>
    )
}

function StateBadge({ state, colorScheme = "gray" }: { state?: string, colorScheme?: string }) {
    if (!state) return <Text color="gray.600">--</Text>;

    // Map states to colors if needed
    let color = colorScheme;
    if (state === 'ENTRY') color = 'green';
    if (state === 'EXIT') color = 'orange';
    if (state === 'ARM') color = 'yellow';

    return (
        <Badge colorScheme={color} variant="solid" px={2} rounded="md">
            {state}
        </Badge>
    );
}

function TrendBadge({ direction }: { direction?: string }) {
    if (direction === 'UP') return <HStack spacing={1} color="green.400"><Icon as={ArrowUp} boxSize={3} /><Text fontSize="xs" fontWeight="bold">UP</Text></HStack>;
    if (direction === 'DOWN') return <HStack spacing={1} color="red.400"><Icon as={ArrowDown} boxSize={3} /><Text fontSize="xs" fontWeight="bold">DOWN</Text></HStack>;
    return <HStack spacing={1} color="gray.500"><Icon as={Minus} boxSize={3} /><Text fontSize="xs" fontWeight="bold">FLAT</Text></HStack>;
}

function SignalBadge({ signal }: { signal?: string }) {
    if (signal === 'BUY') return <Text color="green.400" fontWeight="bold">BUY</Text>;
    if (signal === 'SELL') return <Text color="red.400" fontWeight="bold">SELL</Text>;
    return <Text color="gray.500">WAIT</Text>;
}
