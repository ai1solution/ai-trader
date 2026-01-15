// API Proxy for unified container deployment
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
    const path = request.nextUrl.pathname.replace('/api', '');
    const search = request.nextUrl.search;

    try {
        const response = await fetch(`${BACKEND_URL}${path}${search}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json({ error: 'Failed to fetch from backend' }, { status: 500 });
    }
}

export async function POST(request: NextRequest) {
    const path = request.nextUrl.pathname.replace('/api', '');
    const body = await request.json();

    try {
        const response = await fetch(`${BACKEND_URL}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json({ error: 'Failed to fetch from backend' }, { status: 500 });
    }
}
