'use client';

import { useEffect, useState } from 'react';
import {
    Box,
    VStack,
    HStack,
    Text,
    Heading,
    Icon,
    Flex,
    Badge,
    Skeleton,
    Image,
    Link
} from '@chakra-ui/react';
import { TrendingUp, ExternalLink, Clock } from 'lucide-react';
import axios from 'axios';

interface TrendingArticle {
    title: string;
    link: string;
    snippet: string;
    source: string;
    date: string;
    thumbnail?: string;
}

const SERPAPI_KEY = '37298880d0fcef3adfd0564c3a7cca6fd95b1077fa33677fb1cc5fd1ee21cfb6';
const SERPAPI_BASE = 'https://serpapi.com/search.json';

export function TrendingNews() {
    const [news, setNews] = useState<TrendingArticle[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTrending = async () => {
            try {
                const response = await axios.get(SERPAPI_BASE, {
                    params: {
                        engine: 'google_news',
                        q: 'Bitcoin cryptocurrency trending',
                        api_key: SERPAPI_KEY,
                        num: 3,
                        gl: 'us',
                        hl: 'en'
                    },
                    timeout: 10000
                });

                const newsResults = response.data.news_results || [];
                const articles: TrendingArticle[] = newsResults.slice(0, 3).map((item: any) => ({
                    title: item.title || '',
                    link: item.link || '',
                    snippet: item.snippet || '',
                    source: item.source?.name || 'Unknown',
                    date: item.date || '',
                    thumbnail: item.thumbnail || ''
                }));

                setNews(articles);
            } catch (err) {
                console.error('Trending news error:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchTrending();
        // Refresh every 10 minutes
        const interval = setInterval(fetchTrending, 600000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <VStack spacing={3} align="stretch">
                {[1, 2, 3].map(i => (
                    <Box key={i} p={4} bg="gray.900" rounded="lg" borderWidth={1} borderColor="whiteAlpha.100">
                        <Skeleton height="60px" />
                    </Box>
                ))}
            </VStack>
        );
    }

    return (
        <VStack spacing={3} align="stretch">
            <HStack mb={2}>
                <Icon as={TrendingUp} boxSize={5} color="orange.400" />
                <Heading size="sm" color="white">Trending on Bitcoin</Heading>
                <Badge colorScheme="orange" variant="subtle" fontSize="xs">LIVE</Badge>
            </HStack>

            {news.map((article, idx) => (
                <Box
                    key={idx}
                    p={4}
                    bg="gray.900"
                    rounded="lg"
                    borderWidth={1}
                    borderColor="whiteAlpha.100"
                    cursor="pointer"
                    _hover={{
                        borderColor: 'orange.400',
                        transform: 'scale(1.02)',
                        boxShadow: '0 4px 12px rgba(251, 146, 60, 0.15)'
                    }}
                    transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
                    onClick={() => window.open(article.link, '_blank')}
                >
                    <HStack align="start" spacing={3}>
                        {article.thumbnail && (
                            <Box
                                w="50px"
                                h="50px"
                                rounded="md"
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
                        <VStack align="start" flex={1} spacing={1}>
                            <Text fontSize="sm" fontWeight="bold" color="white" lineHeight="shorter" noOfLines={2}>
                                {article.title}
                            </Text>
                            <Flex justify="space-between" w="full" fontSize="xs" color="gray.500">
                                <HStack spacing={2}>
                                    <Text>{article.source}</Text>
                                    {article.date && (
                                        <>
                                            <Text>•</Text>
                                            <HStack spacing={1}>
                                                <Icon as={Clock} boxSize={3} />
                                                <Text>{article.date}</Text>
                                            </HStack>
                                        </>
                                    )}
                                </HStack>
                                <Icon as={ExternalLink} boxSize={3} color="orange.400" />
                            </Flex>
                        </VStack>
                    </HStack>
                </Box>
            ))}
        </VStack>
    );
}
