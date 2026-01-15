import { Box, SimpleGrid, Skeleton, Flex, HStack } from '@chakra-ui/react';

export function SkeletonEngineCard() {
    return (
        <Box
            p={5}
            bg="gray.900"
            rounded="xl"
            borderWidth={1}
            borderColor="whiteAlpha.100"
            h="200px"
        >
            <Flex justify="space-between" mb={3}>
                <Skeleton height="20px" width="100px" />
                <Skeleton height="16px" width="60px" rounded="full" />
            </Flex>

            <Skeleton height="32px" width="120px" mb={4} />

            <SimpleGrid columns={2} spacing={3}>
                <Skeleton height="60px" rounded="lg" />
                <Skeleton height="60px" rounded="lg" />
                <Skeleton height="60px" rounded="lg" />
                <Skeleton height="60px" rounded="lg" />
            </SimpleGrid>
        </Box>
    );
}

export function SkeletonEngineGrid() {
    return (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} spacing={4} w="full">
            {[1, 2, 3, 4].map(i => (
                <SkeletonEngineCard key={i} />
            ))}
        </SimpleGrid>
    );
}
