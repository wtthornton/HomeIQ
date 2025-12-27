# NumPy Best Practices from Context7 Research

**Date:** October 24, 2025  
**Source:** Context7 Research on `/numpy/numpy`  
**Purpose:** Knowledge base for NumPy development best practices

## Array Methods vs Functions

### ❌ Common Mistakes
```python
# WRONG - Arrays don't have these methods
array.norm()      # ❌ Use np.linalg.norm(array)
array.sum()       # ❌ Use np.sum(array) or array.sum() (this one actually works)
array.min()       # ❌ Use np.min(array) or array.min() (this one actually works)
```

### ✅ Correct Approaches
```python
import numpy as np

# For norms - use np.linalg.norm()
array = np.array([1, 2, 3])
norm_result = np.linalg.norm(array, 2)  # L2 norm
norm_result = np.linalg.norm(array, 1)  # L1 norm
norm_result = np.linalg.norm(array, np.inf)  # Infinity norm

# For multi-dimensional arrays
array_2d = np.array([[1, 2], [3, 4]])
norms = np.linalg.norm(array_2d, axis=1, keepdims=True)  # Norm along rows
```

## Array Manipulation Best Practices

### Flattening Arrays
```python
# .flatten() - creates a copy
x = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
a1 = x.flatten()  # Copy - changes don't affect original
a1[0] = 99  # Original x unchanged

# .ravel() - returns a view
a2 = x.ravel()  # View - changes affect original
a2[0] = 98  # Original x is modified
```

### Reshaping Arrays
```python
# Use -1 to infer dimension
data = np.arange(12)
reshaped = data.reshape(4, -1)  # Automatically calculates 3 columns

# Check if reshape is possible
if data.size == 4 * 3:  # Verify total elements match
    reshaped = data.reshape(4, 3)
```

### Sorting Arrays
```python
# Sort each column
array_2d = np.array([[3, 1, 4], [1, 5, 9]])
sorted_cols = np.sort(array_2d, axis=0)  # Sort along columns
sorted_rows = np.sort(array_2d, axis=1)  # Sort along rows

# In-place sorting
array_2d.sort(axis=0)  # Sort columns in-place
```

## Data Type Preservation

### Float Type Preservation
```python
# NumPy preserves input types in many operations
f32 = np.float32([1, 2])
result = np.linalg.norm(f32, 2)  # Result is float32, not float64

# This is important for memory efficiency
f16 = np.float16([1, 2])
result = np.linalg.norm(f16, 2)  # Result is float16
```

### Type Conversion
```python
# Convert to NumPy array
custom_array = DiagonalArray()  # Custom array-like object
numpy_array = np.asarray(custom_array)  # Converts to numpy.ndarray

# Structured to unstructured conversion
structured = np.zeros(3, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4')])
unstructured = structured[['x', 'z']].view('f4')  # Less safe
# Better approach:
from numpy.lib.recfunctions import structured_to_unstructured
unstructured = structured_to_unstructured(structured[['x', 'z']])
```

## Performance Optimizations

### Memory-Efficient Operations
```python
# Use np.empty() when you'll fill the array immediately
empty_array = np.empty(1000)  # Faster than np.zeros() or np.ones()
# Fill with your data...

# Use views when possible
view_array = original_array.ravel()  # No copy, just view
```

### Axis-Specific Operations
```python
# Specify axis for multi-dimensional operations
array_2d = np.arange(12).reshape(3, 4)

# Sum along columns (axis=0)
col_sums = array_2d.sum(axis=0)

# Min along rows (axis=1)  
row_mins = array_2d.min(axis=1)

# Cumulative sum along rows
cumsum_rows = array_2d.cumsum(axis=1)
```

## Error Handling

### Division by Zero
```python
# Safe division with zero handling
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
norms = np.where(norms == 0, 1, norms)  # Replace zeros with 1
normalized = embeddings / norms
```

### NaN Handling
```python
# Handle NaN values in sums
x = np.arange(10.0)
x[3] = np.nan

regular_sum = x.sum()  # Returns NaN
nan_safe_sum = np.nansum(x)  # Ignores NaN values
```

## Array Creation Patterns

### Uninitialized Arrays
```python
# Create uninitialized array (faster when you'll fill it)
uninitialized = np.empty((100, 100))  # Random initial values
# Fill with your data...

# Create with specific shape
zeros_array = np.zeros((3, 4))
ones_array = np.ones((2, 5))
```

### Array Indexing
```python
# Find non-zero elements
z = np.array([[1, 2, 3, 0], [0, 0, 5, 3], [4, 6, 0, 0]])
nonzero_indices = np.nonzero(z)  # Returns tuple of indices

# Boolean indexing
mask = z > 2
filtered = z[mask]  # Elements greater than 2
```

## Integration with Other Libraries

### Sentence Transformers
```python
# When sentence_transformers.util has compatibility issues
# Implement your own normalization:
def safe_normalize_embeddings(embeddings):
    """Safe embedding normalization using pure NumPy"""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return embeddings / norms
```

### PyTorch Integration
```python
# Convert between NumPy and PyTorch
numpy_array = np.array([1, 2, 3])
torch_tensor = torch.from_numpy(numpy_array)  # Shares memory
numpy_back = torch_tensor.numpy()  # Convert back
```

## Testing Patterns

### Array Equality Testing
```python
# Use np.allclose() for floating point comparisons
array1 = np.array([1.0, 2.0, 3.0])
array2 = np.array([1.0000001, 2.0, 3.0])
assert np.allclose(array1, array2)  # Handles floating point precision

# Exact equality for integers
int_array1 = np.array([1, 2, 3])
int_array2 = np.array([1, 2, 3])
assert np.array_equal(int_array1, int_array2)
```

### Shape and Type Validation
```python
def validate_embeddings(embeddings):
    """Validate embedding array properties"""
    assert isinstance(embeddings, np.ndarray), "Must be NumPy array"
    assert embeddings.ndim == 2, "Must be 2D array"
    assert embeddings.shape[1] > 0, "Must have positive embedding dimension"
    assert not np.any(np.isnan(embeddings)), "Cannot contain NaN values"
    return True
```

## Common Pitfalls to Avoid

1. **Don't assume arrays have `.norm()` method** - Use `np.linalg.norm()`
2. **Don't use `array.norm()`** - This doesn't exist in NumPy
3. **Be careful with `.flatten()` vs `.ravel()`** - One copies, one views
4. **Handle division by zero** - Use `np.where()` for safe operations
5. **Preserve data types** - NumPy often preserves input types
6. **Test with edge cases** - Zero vectors, NaN values, empty arrays

## Context7 Sources

- **Primary Source**: `/numpy/numpy` - Official NumPy documentation
- **Research Date**: October 24, 2025
- **Key Topics**: Array methods, linalg operations, data type preservation
- **Code Examples**: 20+ practical examples from Context7 research

---

**Last Updated:** October 24, 2025  
**Next Review:** When upgrading NumPy or encountering new array method issues
