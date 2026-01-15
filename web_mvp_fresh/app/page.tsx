'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import {
    Box,
    Button,
    Container,
    Heading,
    Text,
    VStack,
    HStack,
    Input,
    InputGroup,
    InputLeftElement,
    List,
    ListItem,
    Icon,
    Flex,
    Badge,
    useOutsideClick,
    Grid,
    GridItem,
} from '@chakra-ui/react'
import { Search, TrendingUp, Terminal, Zap, BarChart2, Shield, Activity } from 'lucide-react'
import { useRef } from 'react'
import { ActiveEngineList } from '@/components/ActiveEngineList'
import { NewsPanel } from '@/components/NewsPanel'
import { AIOSLogo } from '@/components/AIOSLogo'
import { TrendingNews } from '@/components/TrendingNews'

const DEFAULT_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT',
    'AVAX/USDT', 'MATIC/USDT', 'DOT/USDT', 'LINK/USDT', 'ATOM/USDT',
    'NEAR/USDT', 'APT/USDT', 'ARB/USDT', 'OP/USDT', 'RUNE/USDT',
    'INJ/USDT', 'SUI/USDT', 'SEI/USDT', 'TIA/USDT', 'PENDLE/USDT'
]

export default function Home() {
    const router = useRouter()
    const [query, setQuery] = useState('')
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const wrapperRef = useRef<any>(null)

    useOutsideClick({
        ref: wrapperRef,
        handler: () => setIsOpen(false),
    })

    const filteredCoins = useMemo(() => {
        if (!query) return DEFAULT_COINS
        return DEFAULT_COINS.filter(coin =>
            coin.toLowerCase().includes(query.toLowerCase())
        )
    }, [query])

    const handleSelect = (symbol: string) => {
        setQuery(symbol)
        setIsOpen(false)
    }

    const handleAnalyze = () => {
        if (!query) return
        setIsLoading(true)
        const slug = encodeURIComponent(query.toUpperCase())
        router.push(`/coin/${slug}`)
    }

    return (
        <Box
            minH="100vh"
            bg="black"
            bgImage="radial-gradient(ellipse at 50% 0%, rgba(79, 70, 229, 0.15) 0%, transparent 70%)"
            color="white"
            display="flex"
            alignItems="center"
            justifyContent="center"
        >
            <Container maxW="container.xl">
                <VStack spacing={8} align="center" textAlign="center">

                    {/* Brand / Logo Area */}
                    <Flex align="center" gap={4} mb={2}>
                        <AIOSLogo size={56} animate={true} />
                        <VStack align="start" spacing={0}>
                            <Heading size="2xl" bgGradient="linear(to-r, brand.400, purple.400)" bgClip="text" fontWeight="extrabold">
                                AIOS
                            </Heading>
                            <Text fontSize="sm" color="gray.500" fontWeight="bold" letterSpacing="wider">
                                AUTONOMOUS INTELLIGENCE OPERATING SYSTEM
                            </Text>
                        </VStack>
                    </Flex>

                    <Box textAlign="center">
                        <Heading
                            as="h2"
                            size="xl"
                            mb={3}
                            color="white"
                            fontWeight="bold"
                        >
                            Multi-Engine Crypto Intelligence
                        </Heading>
                        <Text fontSize="lg" color="gray.400" maxW="2xl" mx="auto">
                            Real-time market regime classification powered by 4 autonomous trading engines.
                            Get institutional-grade insights across momentum, probability, and risk analysis.
                        </Text>
                    </Box>

                    {/* Search / Selection Area */}
                    <Box w="full" maxW="md" position="relative" ref={wrapperRef} pt={8}>
                        <InputGroup size="lg">
                            <InputLeftElement pointerEvents="none">
                                <Icon as={Search} color="gray.500" />
                            </InputLeftElement>
                            <Input
                                placeholder="Search Symbol (e.g. BTC/USDT)"
                                value={query}
                                onChange={(e) => {
                                    setQuery(e.target.value)
                                    setIsOpen(true)
                                }}
                                onFocus={() => setIsOpen(true)}
                                bg="whiteAlpha.50"
                                borderColor="whiteAlpha.200"
                                _hover={{ borderColor: "brand.400" }}
                                _focus={{ borderColor: "brand.500", bg: "whiteAlpha.100", boxShadow: "none" }}
                                fontSize="lg"
                                rounded="xl"
                            />
                        </InputGroup>

                        {/* Dropdown */}
                        {isOpen && filteredCoins.length > 0 && (
                            <Box
                                position="absolute"
                                top="100%"
                                left={0}
                                right={0}
                                mt={2}
                                bg="gray.900"
                                borderColor="gray.800"
                                borderWidth="1px"
                                rounded="xl"
                                shadow="2xl"
                                maxH="300px"
                                overflowY="auto"
                                zIndex={10}
                            >
                                <List spacing={0}>
                                    {filteredCoins.map((coin) => (
                                        <ListItem
                                            key={coin}
                                            px={4}
                                            py={3}
                                            cursor="pointer"
                                            _hover={{ bg: "whiteAlpha.100" }}
                                            onClick={() => handleSelect(coin)}
                                            borderBottomWidth="1px"
                                            borderBottomColor="whiteAlpha.50"
                                            _last={{ borderBottomWidth: 0 }}
                                            display="flex"
                                            alignItems="center"
                                            justifyContent="space-between"
                                        >
                                            <Text fontWeight="bold" fontSize="md">{coin}</Text>
                                            <Icon as={TrendingUp} color="gray.600" boxSize={4} />
                                        </ListItem>
                                    ))}
                                </List>
                            </Box>
                        )}

                        <Button
                            mt={6}
                            size="lg"
                            colorScheme="brand"
                            w="full"
                            h={14}
                            fontSize="lg"
                            rounded="xl"
                            onClick={handleAnalyze}
                            isLoading={isLoading}
                            loadingText="Initializing Engine Link"
                            isDisabled={!query}
                            _disabled={{ opacity: 0.6, cursor: "not-allowed" }}
                            rightIcon={<Icon as={TrendingUp} />}
                        >
                            Analyze Market
                        </Button>
                    </Box>

                    {/* Three Column Layout - Trending / Engines / News */}
                    <Grid
                        templateColumns={{
                            base: "1fr",
                            lg: "300px 1fr 350px"
                        }}
                        gap={{ base: 6, md: 8 }}
                        w="full"
                        maxW="container.xl"
                        pt={{ base: 8, md: 12 }}
                        px={{ base: 4, md: 0 }}
                    >
                        {/* Left: Trending Bitcoin News */}
                        <GridItem order={{ base: 2, lg: 1 }}>
                            <TrendingNews />
                        </GridItem>

                        {/* Center: Active Engines Monitor */}
                        <GridItem order={{ base: 1, lg: 2 }}>
                            <Heading size="md" mb={4} color="white">
                                <HStack>
                                    <Icon as={Activity} boxSize={5} color="brand.400" />
                                    <Text>Live Engines</Text>
                                </HStack>
                            </Heading>
                            <ActiveEngineList />
                        </GridItem>

                        {/* Right: Market News */}
                        <GridItem order={{ base: 3, lg: 3 }}>
                            <NewsPanel />
                        </GridItem>
                    </Grid>

                    {/* Footer / Trust Signal */}
                    <Flex
                        gap={{ base: 4, md: 8 }}
                        pt={8}
                        pb={4}
                        color="gray.600"
                        fontSize={{ base: 'xs', md: 'sm' }}
                        wrap="wrap"
                        justify="center"
                        px={{ base: 4, md: 0 }}
                    >
                        <Flex align="center" gap={2}>
                            <Box w={2} h={2} rounded="full" bg="emerald.500" />
                            <Text>All Systems Online</Text>
                        </Flex>
                        <Flex align="center" gap={2}>
                            <Icon as={Zap} boxSize={3} color="yellow.500" />
                            <Text>Live Market Data</Text>
                        </Flex>
                        <Flex align="center" gap={2}>
                            <Icon as={Activity} boxSize={3} color="blue.500" />
                            <Text>4 Engines Active</Text>
                        </Flex>
                        <Flex align="center" gap={2}>
                            <Icon as={TrendingUp} boxSize={3} color="purple.500" />
                            <Text>Real-Time Analysis</Text>
                        </Flex>
                    </Flex>

                </VStack>
            </Container>
        </Box>
    )
}
