'use client';

import { useEffect, useState } from 'react';
import {
    Box,
    VStack,
    HStack,
    Text,
    Heading,
    Link,
    Icon,
    Flex,
    Badge,
    Skeleton,
    SkeletonText,
    Image
} from '@chakra-ui/react';
import { ExternalLink, TrendingUp, Clock, Newspaper } from 'lucide-react';
import axios from 'axios';

interface NewsArticle {
    title: string;
    link: string;
    snippet: string;
    source: string;
    date: string;
    thumbnail?: string;
}

interface NewsResponse {
    news: NewsArticle[];
    count: number;
}

const SERPAPI_KEY = '37298880d0fcef3adfd0564c3a7cca6fd95b1077fa33677fb1cc5fd1ee21cfb6';
const SERPAPI_BASE = 'https://serpapi.com/search.json';

export function NewsPanel({ symbol }: { symbol?: string }) {
    const [news, setNews] = useState<NewsArticle[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchNews = async () => {
            try {
                setLoading(true);

                // Call backend API instead of SerpAPI directly
                const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
                const endpoint = symbol
                    ? `${API_URL}/news/${encodeURIComponent(symbol)}`
                    : `${API_URL}/news`;

                const response = await axios.get<NewsResponse>(endpoint, {
                    timeout: 10000
                });

                setNews(response.data.news || []);
                setError(null);
            } catch (err) {
                console.error('News fetch error:', err);
                setError('Unable to load news');
            } finally {
                setLoading(false);
            }
        };

        fetchNews();
        const interval = setInterval(fetchNews, 300000); // Refresh every 5 minutes
        return () => clearInterval(interval);
    }, [symbol]);

    if (loading && news.length === 0) {
        return (
            <VStack spacing={4} align="stretch">
                {[1, 2, 3].map(i => (
                    <Box key={i} p={4} bg="gray.900" rounded="xl" borderWidth={1} borderColor="whiteAlpha.100">
                        <Skeleton height="20px" mb={2} />
                        <SkeletonText mt={2} noOfLines={2} spacing={2} />
                    </Box>
                ))}
            </VStack>
        );
    }

    if (error) {
        return (
            <Box p={6} bg="red.900" rounded="xl" borderColor="red.500" borderWidth={1} textAlign="center">
                <Icon as={Newspaper} boxSize={8} color="red.400" mb={2} />
                <Text color="red.200">{error}</Text>
            </Box>
        );
    }

    return (
        <VStack spacing={3} align="stretch">
            <Flex justify="space-between" align="center" mb={2}>
                <HStack>
                    <Icon as={Newspaper} boxSize={5} color="blue.400" />
                    <Heading size="md" color="white">
                        {symbol ? `${symbol.split('/')[0]} News` : 'Market News'}
                    </Heading>
                </HStack>
                <Badge colorScheme="blue" variant="subtle">
                    Live
                </Badge>
            </Flex>

            {news.map((article, idx) => (
                <Box
                    key={idx}
                    p={4}
                    bg="gray.900"
                    rounded="xl"
                    borderWidth={1}
                    borderColor="whiteAlpha.100"
                    _hover={{
                        borderColor: 'blue.400',
                        transform: 'translateX(4px)',
                        boxShadow: '0 4px 12px rgba(59, 130, 246, 0.15)'
                    }}
                    transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
                    cursor="pointer"
                    onClick={() => window.open(article.link, '_blank')}
                >
                    <HStack align="start" spacing={3}>
                        {article.thumbnail && (
                            <Box
                                w="60px"
                                h="60px"
                                rounded="lg"
                                overflow="hidden"
                                flexShrink={0}
                                bg="gray.800"
                            >
                                <Image
                                    src={article.thumbnail}
                                    alt={article.title}
                                    w="full"
                                    h="full"
                                    objectFit="cover"
                                />
                            </Box>
                        )}
                        <VStack align="start" flex={1} spacing={2}>
                            <Heading size="sm" color="white" lineHeight="shorter">
                                {article.title}
                            </Heading>
                            <Text fontSize="sm" color="gray.400" noOfLines={2}>
                                {article.snippet}
                            </Text>
                            <Flex justify="space-between" w="full" fontSize="xs" color="gray.500">
                                <HStack spacing={3}>
                                    <HStack spacing={1}>
                                        <Icon as={TrendingUp} boxSize={3} />
                                        <Text>{article.source}</Text>
                                    </HStack>
                                    {article.date && (
                                        <HStack spacing={1}>
                                            <Icon as={Clock} boxSize={3} />
                                            <Text>{article.date}</Text>
                                        </HStack>
                                    )}
                                </HStack>
                                <Icon as={ExternalLink} boxSize={3} color="blue.400" />
                            </Flex>
                        </VStack>
                    </HStack>
                </Box>
            ))}

            {news.length === 0 && !loading && (
                <Box p={8} textAlign="center" bg="whiteAlpha.50" rounded="xl">
                    <Icon as={Newspaper} boxSize={12} color="gray.600" mb={2} />
                    <Text color="gray.500">No news available</Text>
                </Box>
            )}
        </VStack>
    );
}
