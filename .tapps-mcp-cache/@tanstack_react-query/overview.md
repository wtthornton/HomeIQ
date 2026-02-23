### Basic TanStack Query Setup with useQuery Hook

Demonstrates the fundamental setup of TanStack Query including QueryClient initialization, QueryClientProvider wrapper, and useQuery hook for fetching GitHub repository data. The example shows handling loading states, errors, and displaying fetched data with proper TypeScript support.

```typescript
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Example />
    </QueryClientProvider>
  )
}

function Example() {
  const { isPending, error, data } = useQuery({
    queryKey: ['repoData'],
    queryFn: () =>
      fetch('https://api.github.com/repos/TanStack/query').then((res) =>
        res.json(),
      ),
  })

  if (isPending) return 'Loading...'

  if (error) return 'An error has occurred: ' + error.message

  return (
    <div>
      <h1>{data.name}</h1>
      <p>{data.description}</p>
      <strong>👀 {data.subscribers_count}</strong>{' '}
      <strong>✨ {data.stargazers_count}</strong>{' '}
      <strong>🍴 {data.forks_count}</strong>
    </div>
  )
}
```

### Initialize TanStack Svelte Query Client Provider

This Svelte component demonstrates how to set up the `QueryClientProvider` at the root of a Svelte application. It imports `QueryClient` and `QueryClientProvider` from `@tanstack/svelte-query`, creates a new `QueryClient` instance, and wraps the application's components with the provider to make the query client available throughout the component tree.

```svelte
<script lang="ts">
  import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query'
  import Example from './lib/Example.svelte'

  const queryClient = new QueryClient()
</script>

<QueryClientProvider client={queryClient}>
  <Example />
</QueryClientProvider>
```

### Fetch GitHub Repository Stats using Solid Query (SolidJS)

This SolidJS example demonstrates the basic usage of `@tanstack/solid-query` to fetch data from the GitHub API. It uses `useQuery` to retrieve repository statistics, integrating with SolidJS's `ErrorBoundary` for error handling and `Suspense` for loading states. The query is configured with a `staleTime` for caching and `throwOnError` for robust error propagation.

```tsx
import { ErrorBoundary, Suspense } from 'solid-js'
import {
  useQuery,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/solid-query'

function App() {
  const repositoryQuery = useQuery(() => ({
    queryKey: ['TanStack Query'],
    queryFn: async () => {
      const result = await fetch('https://api.github.com/repos/TanStack/query')
      if (!result.ok) throw new Error('Failed to fetch data')
      return result.json()
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    throwOnError: true, // Throw an error if the query fails
  }))

  return (
    <div>
      <div>Static Content</div>
      {/* An error while fetching will be caught by the ErrorBoundary */}
      <ErrorBoundary fallback={<div>Something went wrong!</div>}>
        {/* Suspense will trigger a loading state while the data is being fetched */}
        <Suspense fallback={<div>Loading...</div>}>
          {/* 
            The `data` property on a query is a SolidJS resource  
            so it will work with Suspense and transitions out of the box! 
          */}
          <div>{repositoryQuery.data?.updated_at}</div>
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}

const root = document.getElementById('root')
const client = new QueryClient()

render(
  () => (
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  ),
  root!,
)
```

### Fetch Data with SolidJS createResource and Error Handling

Demonstrates fetching data from a GitHub API using SolidJS createResource with ErrorBoundary and Suspense for handling loading and error states. The example shows how to fetch repository data, handle errors, and display loading states declaratively.

```tsx
import { createResource, ErrorBoundary, Suspense } from 'solid-js'
import { render } from 'solid-js/web'

function App() {
  const [repository] = createResource(async () => {
    const result = await fetch('https://api.github.com/repos/TanStack/query')
    if (!result.ok) throw new Error('Failed to fetch data')
    return result.json()
  })

  return (
    <div>
      <div>Static Content</div>
      {/* An error while fetching will be caught by the ErrorBoundary */}
      <ErrorBoundary fallback={<div>Something went wrong!</div>}>
        {/* Suspense will trigger a loading state while the data is being fetched */}
        <Suspense fallback={<div>Loading...</div>}>
          <div>{repository()?.updated_at}</div>
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}

const root = document.getElementById('root')

render(() => <App />, root!)
```

### Handle Mutation Outcome with `onSettled` in TanStack Query (TSX)

This example illustrates using the `onSettled` callback within TanStack Query's `useMutation` as a single handler for both success and error scenarios. It can replace separate `onError` and `onSuccess` handlers for simplified logic, allowing conditional actions based on the `error` parameter.

```tsx
useMutation({
  mutationFn: updateTodo,
  // ...
  onSettled: async (newTodo, error, variables, onMutateResult, context) => {
    if (error) {
      // do something
    }
  },
})
```

### Fetch Data with createQuery in Svelte

This Svelte component illustrates how to use the `createQuery` function from `@tanstack/svelte-query` to fetch data. It defines a query with a `queryKey` and `queryFn` to fetch a list of todos. The component then conditionally renders loading, error, or success states based on the `query` object's properties, displaying the fetched data.

```svelte
<script lang="ts">
  import { createQuery } from '@tanstack/svelte-query'

  const query = createQuery(() => ({
    queryKey: ['todos'],
    queryFn: () => fetchTodos(),
  }))
</script>

<div>
  {#if query.isLoading}
    <p>Loading...</p>
  {:else if query.isError}
    <p>Error: {query.error.message}</p>
  {:else if query.isSuccess}
    {#each query.data as todo}
      <p>{todo.title}</p>
    {/each}
  {/if}
</div>
```

### Persist and Resume TanStack Query Mutations with Optimistic Updates

This snippet demonstrates how to define a mutation with optimistic updates using `setMutationDefaults`, persist its state with `dehydrate` when the application quits, and then `hydrate` and `resumePausedMutations` when the application restarts. It includes `onMutate`, `onSuccess`, and `onError` callbacks for managing optimistic UI.

```tsx
const queryClient = new QueryClient()

// Define the "addTodo" mutation
queryClient.setMutationDefaults(['addTodo'], {
  mutationFn: addTodo,
  onMutate: async (variables, context) => {
    // Cancel current queries for the todos list
    await context.client.cancelQueries({ queryKey: ['todos'] })

    // Create optimistic todo
    const optimisticTodo = { id: uuid(), title: variables.title }

    // Add optimistic todo to todos list
    context.client.setQueryData(['todos'], (old) => [...old, optimisticTodo])

    // Return a result with the optimistic todo
    return { optimisticTodo }
  },
  onSuccess: (result, variables, onMutateResult, context) => {
    // Replace optimistic todo in the todos list with the result
    context.client.setQueryData(['todos'], (old) =>
      old.map((todo) =>
        todo.id === onMutateResult.optimisticTodo.id ? result : todo,
      ),
    )
  },
  onError: (error, variables, onMutateResult, context) => {
    // Remove optimistic todo from the todos list
    context.client.setQueryData(['todos'], (old) =>
      old.filter((todo) => todo.id !== onMutateResult.optimisticTodo.id),
    )
  },
  retry: 3,
})

// Start mutation in some component:
const mutation = useMutation({ mutationKey: ['addTodo'] })
mutation.mutate({ title: 'title' })

// If the mutation has been paused because the device is for example offline,
// Then the paused mutation can be dehydrated when the application quits:
const state = dehydrate(queryClient)

// The mutation can then be hydrated again when the application is started:
hydrate(queryClient, state)

// Resume the paused mutations:
queryClient.resumePausedMutations()
```

### Handling Multiple Sequential Mutations and Callback Scope

This TypeScript example illustrates the behavior of `injectMutation` when multiple mutations are triggered in a loop. It highlights that `onSuccess` callbacks defined directly on the `mutate` function will only execute for the *last* mutation in the sequence, regardless of which mutation resolves first, while the `onSuccess` defined in the `injectMutation` configuration will fire for each successful mutation.

```ts
export class Example {
  mutation = injectMutation(() => ({
    mutationFn: addTodo,
    onSuccess: (data, variables, onMutateResult, context) => {
      // Will be called 3 times
    },
  }))

  doMutations() {
    ;['Todo 1', 'Todo 2', 'Todo 3'].forEach((todo) => {
      this.mutation.mutate(todo, {
        onSuccess: (data, variables, onMutateResult, context) => {
          // Will execute only once, for the last mutation (Todo 3),
          // regardless which mutation resolves first
        },
      })
    })
  }
}
```

### Define TanStack Query Mutation Scope for Serial Execution

This snippet illustrates how to use the `scope` option with an `id` in `useMutation` to ensure that mutations with the same scope run in serial. This prevents parallel execution of multiple invocations of the same mutation, queuing them instead to run one after another.

```tsx
const mutation = useMutation({
  mutationFn: addTodo,
  scope: {
    id: 'todo',
  },
})
```

### Resume Paused Mutations - TanStack Query

Resumes mutations that were automatically paused due to network disconnection. This method should be called when network connectivity is restored to retry pending mutations.

```typescript
queryClient.resumePausedMutations()
```