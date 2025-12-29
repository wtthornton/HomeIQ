
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    include: [
      "src\__tests__\apiUsageCalculator.test.ts", "src\__tests__\useTeamPreferences.test.ts", "src\hooks\__tests__\useStatistics.test.ts", "node_modules\until-async\src\until.test.ts", "node_modules\react-use-websocket\src\lib\attach-listener.test.ts", "node_modules\react-use-websocket\src\lib\attach-shared-listeners.test.ts", "node_modules\react-use-websocket\src\lib\create-or-join.test.ts", "node_modules\react-use-websocket\src\lib\get-url.test.ts", "node_modules\react-use-websocket\src\lib\globals.test.ts", "node_modules\react-use-websocket\src\lib\heartbeat.test.ts", "node_modules\react-use-websocket\src\lib\manage-subscribers.test.ts", "node_modules\react-use-websocket\src\lib\proxy.test.ts", "node_modules\react-use-websocket\src\lib\socket-io.test.ts", "node_modules\react-use-websocket\src\lib\use-event-source.test.ts", "node_modules\react-use-websocket\src\lib\use-websocket.test.ts", "node_modules\msw\src\core\bypass.test.ts", "node_modules\msw\src\core\getResponse.test.ts", "node_modules\msw\src\core\graphql.test.ts", "node_modules\msw\src\core\http.test.ts", "node_modules\msw\src\core\HttpResponse.test.ts", "node_modules\msw\src\core\passthrough.test.ts", "node_modules\msw\src\core\ws.test.ts", "node_modules\msw\src\core\handlers\GraphQLHandler.test.ts", "node_modules\msw\src\core\handlers\HttpHandler.test.ts", "node_modules\msw\src\core\handlers\WebSocketHandler.test.ts", "node_modules\msw\src\core\utils\handleRequest.test.ts", "node_modules\msw\src\core\ws\WebSocketClientManager.test.ts", "node_modules\msw\src\core\ws\utils\getMessageLength.test.ts", "node_modules\msw\src\core\ws\utils\getPublicData.test.ts", "node_modules\msw\src\core\ws\utils\truncateMessage.test.ts", "node_modules\msw\src\core\utils\internal\devUtils.test.ts", "node_modules\msw\src\core\utils\internal\getCallFrame.test.ts", "node_modules\msw\src\core\utils\internal\isHandlerKind.test.ts", "node_modules\msw\src\core\utils\internal\isIterable.test.ts", "node_modules\msw\src\core\utils\internal\isObject.test.ts", "node_modules\msw\src\core\utils\internal\isStringEqual.test.ts", "node_modules\msw\src\core\utils\internal\jsonParse.test.ts", "node_modules\msw\src\core\utils\internal\mergeRight.test.ts", "node_modules\msw\src\core\utils\internal\parseGraphQLRequest.test.ts", "node_modules\msw\src\core\utils\internal\parseMultipartData.test.ts", "node_modules\msw\src\core\utils\internal\pipeEvents.test.ts", "node_modules\msw\src\core\utils\internal\toReadonlyArray.test.ts", "node_modules\msw\src\core\utils\internal\tryCatch.test.ts", "node_modules\msw\src\core\utils\logging\getStatusCodeColor.test.ts", "node_modules\msw\src\core\utils\logging\getTimestamp.test.ts", "node_modules\msw\src\core\utils\logging\serializeRequest.test.ts", "node_modules\msw\src\core\utils\logging\serializeResponse.test.ts", "node_modules\msw\src\core\utils\matching\matchRequestUrl.test.ts", "node_modules\msw\src\core\utils\matching\normalizePath.node.test.ts", "node_modules\msw\src\core\utils\matching\normalizePath.test.ts", "node_modules\msw\src\core\utils\request\onUnhandledRequest.test.ts", "node_modules\msw\src\core\utils\request\toPublicUrl.test.ts", "node_modules\msw\src\core\utils\url\cleanUrl.test.ts", "node_modules\msw\src\core\utils\url\getAbsoluteUrl.node.test.ts", "node_modules\msw\src\core\utils\url\getAbsoluteUrl.test.ts", "node_modules\msw\src\core\utils\url\isAbsoluteUrl.test.ts", "node_modules\msw\src\browser\setupWorker\setupWorker.node.test.ts", "node_modules\msw\src\browser\utils\getAbsoluteWorkerUrl.test.ts", "node_modules\msw\src\browser\utils\pruneGetRequestBody.test.ts", "node_modules\msw\src\browser\setupWorker\stop\utils\printStopMessage.test.ts", "node_modules\msw\src\browser\setupWorker\start\utils\prepareStartHandler.test.ts", "node_modules\msw\src\browser\setupWorker\start\utils\printStartMessage.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\bun\bun-custom-expect-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\bun\bun-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\jest\jest-custom-expect-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\jest\jest-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\jest-globals\jest-globals-custom-expect-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\jest-globals\jest-globals-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\vitest\vitest-custom-expect-types.test.ts", "node_modules\@testing-library\jest-dom\types\__tests__\vitest\vitest-types.test.ts", "node_modules\@mswjs\interceptors\src\BatchInterceptor.test.ts", "node_modules\@mswjs\interceptors\src\createRequestId.test.ts", "node_modules\@mswjs\interceptors\src\Interceptor.test.ts", "node_modules\@mswjs\interceptors\src\RequestController.test.ts", "node_modules\@mswjs\interceptors\src\utils\bufferUtils.test.ts", "node_modules\@mswjs\interceptors\src\utils\cloneObject.test.ts", "node_modules\@mswjs\interceptors\src\utils\createProxy.test.ts", "node_modules\@mswjs\interceptors\src\utils\findPropertySource.test.ts", "node_modules\@mswjs\interceptors\src\utils\getCleanUrl.test.ts", "node_modules\@mswjs\interceptors\src\utils\getUrlByRequestOptions.test.ts", "node_modules\@mswjs\interceptors\src\utils\getValueBySymbol.test.ts", "node_modules\@mswjs\interceptors\src\utils\hasConfigurableGlobal.test.ts", "node_modules\@mswjs\interceptors\src\utils\isObject.test.ts", "node_modules\@mswjs\interceptors\src\utils\parseJson.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\ClientRequest\index.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\Socket\MockSocket.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\XMLHttpRequest\utils\concateArrayBuffer.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\XMLHttpRequest\utils\createEvent.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\XMLHttpRequest\utils\getBodyByteLength.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\WebSocket\utils\bindEvent.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\WebSocket\utils\events.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\Socket\utils\normalizeSocketWriteArgs.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\ClientRequest\utils\getIncomingMessageBody.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\ClientRequest\utils\normalizeClientRequestArgs.test.ts", "node_modules\@mswjs\interceptors\src\interceptors\ClientRequest\utils\recordRawHeaders.test.ts", "src\components\__tests__\EnvironmentHealthCard.test.tsx"
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**',
      '**/integration/**',
      '**/visual/**',
      '**/*.integration.test.*',
      '**/*.e2e.test.*',
      '**/*.visual.test.*'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      reportsDirectory: '../../test-results/coverage/typescript',
      include: ['src/**/*'],
      exclude: [
        'src/**/*.test.*',
        'src/**/*.spec.*',
        'src/tests/**',
        'src/**/__tests__/**',
        'src/**/*.stories.*',
        'src/**/*.config.*'
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        }
      }
    },
    globals: true,
    setupFiles: ['./src/tests/setup.ts']
  }
})
