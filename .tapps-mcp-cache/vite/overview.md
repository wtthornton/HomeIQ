### Recommended Project Structure

Illustrates a recommended project structure for an Electron application using Vite, highlighting the placement of the Electron main process file and the Vite configuration file.

```diff
+ ├─┬ electron
+ │ └── main.ts
  ├─┬ src
  │ ├── main.ts
  │ ├── style.css
  │ └── vite-env.d.ts
  ├── .gitignore
  ├── favicon.svg
  ├── index.html
  ├── package.json
  ├── tsconfig.json
+ └── vite.config.ts
```

### Electron Main Process Entry Point

Example of an Electron main process entry point (`electron/main.ts`) that creates a BrowserWindow and loads the application content.

```typescript
import { app, BrowserWindow } from 'electron'

app.whenReady().then(() => {
  const win = new BrowserWindow({
    title: 'Main window',
  })

  // You can use `process.env.VITE_DEV_SERVER_URL` when the vite command is called `serve`
  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    // Load your file
    win.loadFile('dist/index.html');
  }
})
```

### Build Formats (CommonJS Type - Default)

Details the output formats and file suffixes for the main process, preload scripts, and renderer process when the project uses the default CommonJS module type.

```log
{ "type": "commonjs" } - default
┏————————————————————┳——————————┳———————————┓
│       built        │  format  │   suffix  │
┠————————————————————╂——————————╂———————————┨
│ main process       │   cjs    │    .js    │
┠————————————————————╂——————————╂———————————┨
│ preload scripts    │   cjs    │    .js    │ diff
┠————————————————————╂——————————╂———————————┨
│ renderer process   │    -     │    .js    │
┗————————————————————┸——————————┸———————————┛
```

### Build Formats (Module Type)

Details the output formats and file suffixes for the main process, preload scripts, and renderer process when the project is configured with `"type": "module"`.

```log
{ "type": "module" }
┏————————————————————┳——————————┳———————————┓
│       built        │  format  │   suffix  │
┠————————————————————╂——————————╂———————————┨
│ main process       │   esm    │    .js    │
┠————————————————————╂——————————╂———————————┨
│ preload scripts    │   cjs    │   .mjs    │ diff
┠————————————————————╂——————————╂———————————┨
│ renderer process   │    -     │    .js    │
┗————————————————————┸——————————┸———————————┛
```

### Update package.json for Electron Main Entry

Adds the 'main' field to package.json to specify the compiled main process entry point for Electron.

```json
{
  "main": "dist-electron/main.mjs"
}
```

### ElectronOptions Interface

Defines the configuration options for the vite-plugin-electron plugin. It allows specifying the entry point, Vite configuration, and a callback for when the Electron app starts.

```ts
export interface ElectronOptions {
  /**
   * Shortcut of `build.lib.entry`
   */
  entry?: import('vite').LibraryOptions['entry']
  vite?: import('vite').InlineConfig
  /**
   * Triggered when Vite is built every time -- `vite serve` command only.
   *
   * If this `onstart` is passed, Electron App will not start automatically.
   * However, you can start Electroo App via `startup` function.
   */
  onstart?: (args: {
    /**
     * Electron App startup function.
     * It will mount the Electron App child-process to `process.electronApp`.
     * @param argv default value `['.', '--no-sandbox']`
     * @param options options for `child_process.spawn`
     * @param customElectronPkg custom electron package name (default: 'electron')
     */
    startup: (argv?: string[], options?: import('node:child_process').SpawnOptions, customElectronPkg?: string) => Promise<void>
    /** Reload Electron-Renderer */
    reload: () => void
  }) => void | Promise<void>
}
```

### vite-plugin-electron JavaScript API Reference

Provides a reference to the core JavaScript APIs exposed by `vite-plugin-electron`. These functions are designed to be used within your Vite configuration for managing Electron builds and processes.

```APIDOC
vite-plugin-electron JavaScript API:

- `ElectronOptions` - type definition for plugin configuration.
- `resolveViteConfig` - function, Resolves the default Vite `InlineConfig` for building the Electron-Main process.
- `withExternalBuiltins` - function, A utility function for managing external dependencies.
- `build` - function, Initiates the Electron application build process with specified options.
- `startup` - function, Starts or restarts the Electron application.

Usage Recommendation:
It is recommended to use TypeScript or enable JS type checking in your IDE (like VS Code) to leverage the full IntelliSense and validation capabilities of these typed APIs.
```

### Install vite-plugin-electron

Installs the vite-plugin-electron package as a development dependency.

```sh
npm i -D vite-plugin-electron
```

### JavaScript API Usage Example

Demonstrates how to use the `build` and `startup` functions from `vite-plugin-electron` in a Vite configuration file to manage the Electron application build and startup process.

```js
import { build, startup } from 'vite-plugin-electron'

const isDev = process.env.NODE_ENV === 'development'
const isProd = process.env.NODE_ENV === 'production'

build({
  entry: 'electron/main.ts',
  vite: {
    mode: process.env.NODE_ENV,
    build: {
      minify: isProd,
      watch: isDev ? {} : null,
    },
    plugins: [{
      name: 'plugin-start-electron',
      closeBundle() {
        if (isDev) {
          // Startup Electron App
          startup()
        }
      },
    }],
  },
})
```

### Configure External Node.js Modules

Demonstrates how to configure external Node.js modules within the Vite build process for vite-plugin-electron. This is particularly useful for native C/C++ modules that Vite might not build correctly. The `external` option in Rollup's configuration prevents Vite from bundling these modules, allowing them to be loaded as external packages.

```javascript
electron({
  entry: 'electron/main.ts',
  vite: {
    build: {
      rollupOptions: {
        // Here are some C/C++ modules them can't be built properly.
        external: [
          'serialport',
          'sqlite3',
        ],
      },
    },
  },
}),
```