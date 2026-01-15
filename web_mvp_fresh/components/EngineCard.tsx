'use client'

import { Box, Card, Flex, Heading, Text, Badge, Progress, Icon } from '@chakra-ui/react'
import { Activity, ShieldCheck, Zap, PauseCircle } from 'lucide-react'

interface EngineCardProps {
    version: string
    name: string
    state: string
    insight: string
    confidence?: number // 0-100
}

export default function EngineCard({ version, name, state, insight, confidence }: EngineCardProps) {

    const getStateColor = (s: string) => {
        switch (s?.toUpperCase()) {
            case 'RUNNING':
            case 'ARM':
            case 'TRENDING':
                return 'emerald'
            case 'STARTING':
            case 'HOLD':
                return 'amber'
            case 'STOPPED':
            case 'ERROR':
                return 'red'
            case 'IDLE':
            case 'RANGING':
                return 'gray'
            default: return 'blue'
        }
    }

    const colorScheme = getStateColor(state)

    return (
        <Card
            bg="gray.900"
            borderColor="gray.800"
            borderWidth="1px"
            overflow="hidden"
            _hover={{ borderColor: "gray.700" }}
            transition="all 0.2s"
        >
            <Box p={5}>
                <Flex justify="space-between" align="start" mb={3}>
                    <Box>
                        <Flex align="center" gap={2} mb={1}>
                            <Badge variant="subtle" colorScheme="purple" fontSize="xs">
                                {version}
                            </Badge>
                            <Text fontSize="xs" color="gray.500" fontWeight="bold" letterSpacing="wide">
                                {name.toUpperCase()}
                            </Text>
                        </Flex>
                    </Box>
                    <Badge colorScheme={colorScheme} variant="solid" rounded="full" px={2} fontSize="xx-small">
                        {state || 'UNKNOWN'}
                    </Badge>
                </Flex>

                <Text fontSize="sm" color="gray.300" minH="3em" noOfLines={3}>
                    {insight || "Waiting for engine telemetry..."}
                </Text>

                {confidence !== undefined && (
                    <Box mt={4}>
                        <Flex justify="space-between" mb={1}>
                            <Text fontSize="xs" color="gray.600">Confidence</Text>
                            <Text fontSize="xs" color="gray.400">{confidence}%</Text>
                        </Flex>
                        <Progress
                            value={confidence}
                            size="xs"
                            colorScheme={confidence > 80 ? "emerald" : confidence > 50 ? "blue" : "gray"}
                            rounded="full"
                            bg="gray.800"
                        />
                    </Box>
                )}
            </Box>
        </Card>
    )
}
