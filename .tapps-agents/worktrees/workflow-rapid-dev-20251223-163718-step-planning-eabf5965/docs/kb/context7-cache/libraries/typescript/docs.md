# TypeScript Documentation Cache

## Overview
TypeScript is a strongly typed programming language that builds on JavaScript, giving you better tooling at any scale. This cache contains focused documentation on types, interfaces, and generics.

## Type System Fundamentals

### Basic Types
- **Primitive types**: string, number, boolean, null, undefined
- **Array types**: Array<T> or T[]
- **Tuple types**: [string, number] for fixed-length arrays
- **Enum types**: Custom enumeration types
- **Any type**: Opt-out of type checking
- **Unknown type**: Type-safe alternative to any

### Interface Definitions
- **Object interfaces**: Defining object shapes
- **Optional properties**: Properties that may not exist
- **Readonly properties**: Immutable properties
- **Function interfaces**: Function type definitions
- **Index signatures**: Dynamic property access
- **Extending interfaces**: Inheritance and composition

### Generic Programming
- **Generic functions**: Type-safe reusable functions
- **Generic classes**: Type-safe class definitions
- **Generic constraints**: Limiting generic types
- **Conditional types**: Type-level conditionals
- **Mapped types**: Transforming existing types
- **Template literal types**: String manipulation at type level

### Advanced Type Features
- **Union types**: Types that can be one of several types
- **Intersection types**: Types that combine multiple types
- **Type guards**: Runtime type checking
- **Type assertions**: Explicit type casting
- **Discriminated unions**: Pattern matching with types
- **Utility types**: Built-in type transformations

### Compilation and Configuration
- **tsconfig.json**: TypeScript compiler configuration
- **Module resolution**: Import/export handling
- **Declaration files**: .d.ts files for type definitions
- **Source maps**: Debugging support
- **Incremental compilation**: Faster build times
- **Project references**: Multi-project setups

## Best Practices
- **Strict mode**: Enable strict type checking
- **Type inference**: Let TypeScript infer types when possible
- **Interface vs type**: When to use each
- **Generic constraints**: Proper use of generic limitations
- **Error handling**: Type-safe error patterns
- **Performance**: Compilation optimization techniques
