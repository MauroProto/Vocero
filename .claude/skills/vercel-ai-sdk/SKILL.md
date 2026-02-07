---
name: vercel-ai-sdk
description: Build AI-powered applications with Vercel AI SDK. Use when implementing chat interfaces, text generation, streaming responses, tool calling, or AI agents. Covers providers (OpenAI, Anthropic), streaming patterns, and best practices.
---

# Vercel AI SDK Skill

## Overview

Guide development with Vercel AI SDK for building AI-powered applications. Focus on streaming responses, multi-provider support, tool calling, and production-ready patterns.

## When to Use This Skill

Activate when the user:
- Builds chat interfaces or AI assistants
- Implements text or object generation
- Needs streaming AI responses
- Works with multiple AI providers
- Implements tool calling / function calling
- Builds AI agents with autonomous actions
- Creates RAG (Retrieval Augmented Generation) systems

## Core Concepts

### SDK Structure

```typescript
// AI SDK Core - Server-side generation
import { generateText, streamText, generateObject } from 'ai';

// AI SDK UI - React hooks for chat interfaces
import { useChat, useCompletion, useObject } from 'ai/react';

// Provider packages
import { openai } from '@ai-sdk/openai';
import { anthropic } from '@ai-sdk/anthropic';
import { google } from '@ai-sdk/google';
```

## Text Generation

### Basic Generation

```typescript
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const { text } = await generateText({
  model: openai('gpt-4o'),
  prompt: 'Explain quantum computing in simple terms.',
});
```

### With System Prompt and Messages

```typescript
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const { text } = await generateText({
  model: openai('gpt-4o'),
  system: 'You are a helpful assistant specializing in business formation.',
  messages: [
    { role: 'user', content: 'What documents do I need to form an LLC?' }
  ],
});
```

### Using Anthropic Claude

```typescript
import { generateText } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';

const { text } = await generateText({
  model: anthropic('claude-sonnet-4-20250514'),
  prompt: 'Generate a business plan outline.',
});
```

## Streaming Responses

### Server-Side Streaming

```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

const result = streamText({
  model: openai('gpt-4o'),
  prompt: 'Write a detailed guide on LLC formation.',
});

// Stream as text
for await (const textPart of result.textStream) {
  process.stdout.write(textPart);
}

// Or get full result after streaming
const finalText = await result.text;
```

### Next.js API Route (App Router)

```typescript
// app/api/chat/route.ts
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o'),
    system: 'You are a helpful business assistant.',
    messages,
  });

  return result.toDataStreamResponse();
}
```

### React Client with useChat

```tsx
'use client';

import { useChat } from 'ai/react';

export function ChatInterface() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, error } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`p-3 rounded-lg ${
              message.role === 'user' ? 'bg-blue-100 ml-auto' : 'bg-gray-100'
            } max-w-[80%]`}
          >
            {message.content}
          </div>
        ))}
      </div>

      {error && (
        <div className="p-2 text-red-500 text-sm">{error.message}</div>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="Type your message..."
            className="flex-1 p-2 border rounded"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
```

## Structured Object Generation

### Generate Typed Objects with Zod

```typescript
import { generateObject } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

const companySchema = z.object({
  name: z.string().describe('The company name'),
  industry: z.string().describe('Primary industry'),
  description: z.string().describe('Brief company description'),
  services: z.array(z.string()).describe('List of services offered'),
  targetMarket: z.enum(['B2B', 'B2C', 'Both']).describe('Target market'),
});

const { object } = await generateObject({
  model: openai('gpt-4o'),
  schema: companySchema,
  prompt: 'Generate a fictional tech startup profile.',
});

// object is fully typed as z.infer<typeof companySchema>
console.log(object.name, object.services);
```

### Streaming Objects

```typescript
import { streamObject } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

const result = streamObject({
  model: openai('gpt-4o'),
  schema: z.object({
    title: z.string(),
    sections: z.array(z.object({
      heading: z.string(),
      content: z.string(),
    })),
  }),
  prompt: 'Generate a business plan structure.',
});

for await (const partialObject of result.partialObjectStream) {
  console.log(partialObject); // Partial object as it streams
}
```

## Tool Calling / Function Calling

### Define and Execute Tools

```typescript
import { generateText, tool } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

const result = await generateText({
  model: openai('gpt-4o'),
  tools: {
    getCompanyInfo: tool({
      description: 'Get information about a company by ID',
      parameters: z.object({
        companyId: z.string().describe('The company ID to look up'),
      }),
      execute: async ({ companyId }) => {
        // Call your API or database
        const company = await fetchCompanyById(companyId);
        return company;
      },
    }),
    calculateFees: tool({
      description: 'Calculate formation fees for a state',
      parameters: z.object({
        state: z.string().describe('US state code'),
        entityType: z.enum(['LLC', 'Corporation', 'Partnership']),
      }),
      execute: async ({ state, entityType }) => {
        const fees = await getStateFees(state, entityType);
        return { state, entityType, totalFees: fees };
      },
    }),
  },
  prompt: 'What are the LLC formation fees for Wyoming?',
});

// Access tool calls and results
console.log(result.toolCalls);
console.log(result.toolResults);
console.log(result.text);
```

### Multi-Step Tool Execution

```typescript
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const result = await generateText({
  model: openai('gpt-4o'),
  tools: { /* ... tools */ },
  maxSteps: 5, // Allow up to 5 tool call rounds
  prompt: 'Research company ABC123 and calculate their renewal fees.',
});
```

## AI Agents

### Building an Agent with Tools

```typescript
import { generateText, tool } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';
import { z } from 'zod';

async function runAgent(userQuery: string) {
  const result = await generateText({
    model: anthropic('claude-sonnet-4-20250514'),
    system: `You are a business formation assistant. You help users:
    - Research company formation requirements
    - Calculate fees and timelines
    - Generate required documents

    Use the available tools to gather information before responding.`,
    tools: {
      searchRequirements: tool({
        description: 'Search formation requirements for a state',
        parameters: z.object({
          state: z.string(),
          entityType: z.string(),
        }),
        execute: async ({ state, entityType }) => {
          return await getFormationRequirements(state, entityType);
        },
      }),
      getTimeline: tool({
        description: 'Get estimated formation timeline',
        parameters: z.object({
          state: z.string(),
          expedited: z.boolean(),
        }),
        execute: async ({ state, expedited }) => {
          return await getFormationTimeline(state, expedited);
        },
      }),
      generateDocument: tool({
        description: 'Generate a formation document',
        parameters: z.object({
          documentType: z.enum(['articles', 'operating_agreement', 'ein_application']),
          companyData: z.object({
            name: z.string(),
            state: z.string(),
            members: z.array(z.string()),
          }),
        }),
        execute: async ({ documentType, companyData }) => {
          return await generateFormationDocument(documentType, companyData);
        },
      }),
    },
    maxSteps: 10,
    prompt: userQuery,
  });

  return result.text;
}
```

## Provider Configuration

### OpenAI

```typescript
import { openai, createOpenAI } from '@ai-sdk/openai';

// Default (uses OPENAI_API_KEY env var)
const model = openai('gpt-4o');

// Custom configuration
const customOpenAI = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: 'https://custom-endpoint.com/v1', // For proxies
  compatibility: 'strict',
});

const model = customOpenAI('gpt-4o');
```

### Anthropic

```typescript
import { anthropic, createAnthropic } from '@ai-sdk/anthropic';

// Default (uses ANTHROPIC_API_KEY env var)
const model = anthropic('claude-sonnet-4-20250514');

// With custom config
const customAnthropic = createAnthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Available models
anthropic('claude-sonnet-4-20250514')  // Claude Sonnet 4
anthropic('claude-opus-4-20250514')    // Claude Opus 4
anthropic('claude-3-5-haiku-20241022') // Claude 3.5 Haiku
```

### Google

```typescript
import { google } from '@ai-sdk/google';

const model = google('gemini-1.5-pro');
```

## Next.js Integration Patterns

### Route Handler with Error Handling

```typescript
// app/api/generate/route.ts
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

export const runtime = 'edge'; // Optional: use edge runtime

export async function POST(req: Request) {
  try {
    const { prompt, system } = await req.json();

    if (!prompt) {
      return new Response('Missing prompt', { status: 400 });
    }

    const result = streamText({
      model: openai('gpt-4o'),
      system: system || 'You are a helpful assistant.',
      prompt,
      maxTokens: 1000,
    });

    return result.toDataStreamResponse();
  } catch (error) {
    console.error('AI generation error:', error);
    return new Response('Internal server error', { status: 500 });
  }
}
```

### Server Action

```typescript
// app/actions.ts
'use server';

import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

export async function generateSummary(content: string) {
  const { text } = await generateText({
    model: openai('gpt-4o'),
    prompt: `Summarize the following content:\n\n${content}`,
    maxTokens: 500,
  });

  return text;
}
```

### With Rate Limiting

```typescript
// app/api/chat/route.ts
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '1 m'), // 10 requests per minute
});

export async function POST(req: Request) {
  const ip = req.headers.get('x-forwarded-for') ?? 'anonymous';
  const { success } = await ratelimit.limit(ip);

  if (!success) {
    return new Response('Rate limit exceeded', { status: 429 });
  }

  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o'),
    messages,
  });

  return result.toDataStreamResponse();
}
```

## Advanced Patterns

### Conversation Memory

```typescript
// Store conversation in database
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

async function chat(conversationId: string, userMessage: string) {
  // Load previous messages from database
  const previousMessages = await db.getMessages(conversationId);

  const messages: Message[] = [
    ...previousMessages,
    { role: 'user', content: userMessage },
  ];

  const { text } = await generateText({
    model: openai('gpt-4o'),
    system: 'You are a helpful assistant.',
    messages,
  });

  // Save messages to database
  await db.saveMessages(conversationId, [
    { role: 'user', content: userMessage },
    { role: 'assistant', content: text },
  ]);

  return text;
}
```

### RAG (Retrieval Augmented Generation)

```typescript
import { generateText, embed } from 'ai';
import { openai } from '@ai-sdk/openai';

async function ragQuery(query: string) {
  // 1. Embed the query
  const { embedding } = await embed({
    model: openai.embedding('text-embedding-3-small'),
    value: query,
  });

  // 2. Search vector database
  const relevantDocs = await vectorDb.search(embedding, { topK: 5 });

  // 3. Generate response with context
  const context = relevantDocs.map(doc => doc.content).join('\n\n');

  const { text } = await generateText({
    model: openai('gpt-4o'),
    system: `Answer questions based on the following context. If the answer is not in the context, say so.

Context:
${context}`,
    prompt: query,
  });

  return text;
}
```

### Streaming with Callbacks

```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

const result = streamText({
  model: openai('gpt-4o'),
  prompt: 'Write a story about a startup.',
  onChunk: ({ chunk }) => {
    if (chunk.type === 'text-delta') {
      console.log('Text chunk:', chunk.textDelta);
    }
  },
  onFinish: ({ text, usage }) => {
    console.log('Completed:', text);
    console.log('Tokens used:', usage);
  },
});
```

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_GENERATIVE_AI_API_KEY=...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
```

## Error Handling

```typescript
import { generateText, AIError } from 'ai';
import { openai } from '@ai-sdk/openai';

try {
  const { text } = await generateText({
    model: openai('gpt-4o'),
    prompt: 'Hello',
  });
} catch (error) {
  if (error instanceof AIError) {
    console.error('AI Error:', error.message);
    console.error('Cause:', error.cause);
  } else {
    throw error;
  }
}
```

## Best Practices

### 1. Use Streaming for Long Responses

```typescript
// ✅ GOOD - Stream long responses
const result = streamText({
  model: openai('gpt-4o'),
  prompt: 'Write a detailed analysis...',
});
return result.toDataStreamResponse();

// ❌ BAD - Wait for full response on long content
const { text } = await generateText({
  model: openai('gpt-4o'),
  prompt: 'Write a detailed analysis...',
});
```

### 2. Set Appropriate Token Limits

```typescript
// ✅ GOOD - Set limits based on use case
const { text } = await generateText({
  model: openai('gpt-4o'),
  prompt: 'Generate a brief summary',
  maxTokens: 200,
});
```

### 3. Use Structured Output When Possible

```typescript
// ✅ GOOD - Typed, validated output
const { object } = await generateObject({
  model: openai('gpt-4o'),
  schema: companySchema,
  prompt: 'Extract company info',
});

// ❌ BAD - Parse unstructured text manually
const { text } = await generateText({
  model: openai('gpt-4o'),
  prompt: 'Return company info as JSON',
});
const data = JSON.parse(text); // May fail!
```

### 4. Handle Rate Limits Gracefully

```typescript
import { generateText } from 'ai';

async function generateWithRetry(prompt: string, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await generateText({
        model: openai('gpt-4o'),
        prompt,
      });
    } catch (error) {
      if (error.message?.includes('rate limit') && attempt < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        continue;
      }
      throw error;
    }
  }
}
```

## Prohibited Patterns

❌ **Never:**
- Expose API keys in client-side code
- Stream without proper error boundaries
- Ignore token usage and costs
- Use synchronous generation for real-time UIs
- Trust AI output without validation for critical operations
- Skip rate limiting in production

## Decision Tree

```
What are you building?
├─ Chat interface → useChat hook + streamText API route
├─ Single completion → generateText or streamText
├─ Structured data extraction → generateObject with Zod schema
├─ AI with external actions → Tool calling
└─ Autonomous agent → Multi-step tool calling with maxSteps
```
