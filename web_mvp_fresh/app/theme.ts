import { extendTheme, type ThemeConfig } from '@chakra-ui/react'

const config: ThemeConfig = {
    initialColorMode: 'dark',
    useSystemColorMode: false,
}

const colors = {
    brand: {
        50: '#e0e7ff',
        100: '#c7d2fe',
        200: '#a5b4fc',
        300: '#818cf8',
        400: '#6366f1',
        500: '#4f46e5',
        600: '#4338ca',
        700: '#3730a3',
        800: '#312e81',
        900: '#1e1b4b',
    },
    engine: {
        running: '#10b981', // emerald-500
        starting: '#f59e0b', // amber-500
        error: '#ef4444',    // red-500
        stopped: '#6b7280',  // gray-500
    },
    surface: {
        50: '#f9fafb',
        100: '#f3f4f6',
        200: '#e5e7eb',
        300: '#d1d5db',
        400: '#9ca3af',
        500: '#6b7280',
        600: '#4b5563',
        700: '#374151',
        800: '#1f2937',
        900: '#111827',
    }
}

const theme = extendTheme({
    config,
    colors,
    styles: {
        global: {
            body: {
                bg: '#000000', // Deep black
                color: 'gray.100',
            }
        }
    },
    components: {
        Card: {
            baseStyle: {
                container: {
                    bg: 'gray.900',
                    borderColor: 'gray.800',
                    borderWidth: '1px',
                }
            }
        }
    }
})

export default theme
