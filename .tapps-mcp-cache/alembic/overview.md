### Read Polygon Mesh Data with IPolyMesh

Demonstrates reading polygon mesh data from an Alembic archive. It accesses vertex positions, face indices, counts, UVs, normals, and topology variance at specific time samples. Requires Alembic's Geom and CoreFactory libraries.

```cpp
#include <Alembic/AbcGeom/All.h>
#include <Alembic/AbcCoreFactory/All.h>

using namespace Alembic::AbcGeom;

void readMesh(IPolyMesh& meshObj) {
    IPolyMeshSchema& mesh = meshObj.getSchema();

    std::cout << "Mesh: " << meshObj.getName() << std::endl;
    std::cout << "Samples: " << mesh.getNumSamples() << std::endl;
    std::cout << "Constant: " << (mesh.isConstant() ? "yes" : "no") << std::endl;

    // Check topology variance
    MeshTopologyVariance variance = mesh.getTopologyVariance();
    const char* varStr = (variance == kConstantTopology) ? "Constant" :
                         (variance == kHomogenousTopology) ? "Homogenous" :
                         "Heterogenous";
    std::cout << "Topology: " << varStr << std::endl;

    // Read sample at frame 0
    IPolyMeshSchema::Sample sample;
    mesh.get(sample, ISampleSelector(index_t(0)));

    // Access geometry data
    P3fArraySamplePtr positions = sample.getPositions();
    Int32ArraySamplePtr indices = sample.getFaceIndices();
    Int32ArraySamplePtr counts = sample.getFaceCounts();
    Box3d bounds = sample.getSelfBounds();

    std::cout << "Vertices: " << positions->size() << std::endl;
    std::cout << "Face indices: " << indices->size() << std::endl;
    std::cout << "Faces: " << counts->size() << std::endl;
    std::cout << "Bounds: " << bounds.min << " - " << bounds.max << std::endl;

    // Read UVs if present
    IV2fGeomParam uvParam = mesh.getUVsParam();
    if (uvParam.valid()) {
        IV2fGeomParam::Sample uvSample;
        uvParam.getIndexed(uvSample);
        std::cout << "UVs: " << uvSample.getVals()->size() << std::endl;
        std::cout << "UV indexed: " << (uvParam.isIndexed() ? "yes" : "no") << std::endl;
    }

    // Read normals if present
    IN3fGeomParam normalsParam = mesh.getNormalsParam();
    if (normalsParam.valid()) {
        N3fArraySamplePtr normals = normalsParam.getExpandedValue().getVals();
        std::cout << "Normals: " << normals->size() << std::endl;
    }

    // Iterate through animation
    for (index_t i = 0; i < mesh.getNumSamples(); ++i) {
        mesh.get(sample, ISampleSelector(i));
        // Process each frame...
    }
}

int main() {
    Alembic::AbcCoreFactory::IFactory factory;
    IArchive archive = factory.getArchive("mesh.abc");

    IObject root = archive.getTop();
    for (size_t i = 0; i < root.getNumChildren(); ++i) {
        IObject child(root, root.getChildHeader(i).getName());
        if (IPolyMesh::matches(child.getHeader())) {
            IPolyMesh meshObj(child);
            readMesh(meshObj);
        }
    }
    return 0;
}
```

### Create and Layer Alembic Archives with AbcCoreLayer in C++

Demonstrates creating a base Alembic archive, then creating layered archives for modifications like sparse UV updates, pruning objects, and replacing hierarchies. Finally, it shows how to read these layered archives, where the first specified layer has the highest priority.

```cpp
#include <Alembic/AbcGeom/All.h>
#include <Alembic/AbcCoreOgawa/All.h>
#include <Alembic/AbcCoreFactory/All.h>
#include <Alembic/AbcCoreLayer/Util.h>

using namespace Alembic::AbcGeom;

int main() {
    // Create base archive with original geometry
    {
        OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "base.abc");

        OXform xform(archive.getTop(), "character");
        OPolyMesh mesh(xform, "body");

        // Write original mesh data...
        std::vector<V3f> positions = {V3f(0,0,0), V3f(1,0,0), V3f(0,1,0)};
        std::vector<int32_t> indices = {0, 1, 2};
        std::vector<int32_t> counts = {3};

        OPolyMeshSchema::Sample sample(
            V3fArraySample(positions),
            Int32ArraySample(indices),
            Int32ArraySample(counts)
        );
        mesh.getSchema().set(sample);
    }

    // Create sparse layer with only UV modifications
    {
        OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "uvLayer.abc");

        // Use kSparse to write only specific properties
        OXform xform(archive.getTop(), "character", kSparse);
        OPolyMesh mesh(xform, "body", kSparse);

        // Only set UVs, not full geometry
        OPolyMeshSchema::Sample sample;
        std::vector<V2f> uvs = {V2f(0,0), V2f(1,0), V2f(0.5,1)};
        OV2fGeomParam::Sample uvSample(V2fArraySample(uvs), kFacevaryingScope);
        sample.setUVs(uvSample);
        mesh.getSchema().set(sample);
    }

    // Create layer to prune unwanted objects
    {
        OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "pruneLayer.abc");

        AbcA::MetaData md;
        Alembic::AbcCoreLayer::SetPrune(md, true);  // Mark for pruning

        // This object will be removed when layered
        OObject pruneMe(archive.getTop(), "unwantedObject", md);
    }

    // Create layer to replace hierarchy
    {
        OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "replaceLayer.abc");

        AbcA::MetaData md;
        Alembic::AbcCoreLayer::SetReplace(md, true);  // Mark for replacement

        // This replaces the entire hierarchy below
        OXform replacement(archive.getTop(), "character", md);
        // Add new hierarchy...
    }

    // Read layered archives (first file has priority)
    {
        std::vector<std::string> layers = {
            "uvLayer.abc",      // UV overlay (highest priority)
            "base.abc"          // Base geometry
        };

        Alembic::AbcCoreFactory::IFactory factory;
        Alembic::AbcCoreFactory::IFactory::CoreType coreType;
        IArchive archive = factory.getArchive(layers, coreType);

        if (coreType == Alembic::AbcCoreFactory::IFactory::kLayer) {
            std::cout << "Successfully opened layered archive" << std::endl;

            IObject root = archive.getTop();
            IXform xform(root, "character");
            IPolyMesh mesh(xform, "body");

            // Mesh now has UVs from overlay merged with geometry from base
            if (mesh.getSchema().getUVsParam().valid()) {
                std::cout << "UVs successfully layered" << std::endl;
            }
        }
    }

    return 0;
}
```

### Create and Write Alembic Archive with Time Sampling (C++)

Demonstrates how to create an Alembic archive and define different time sampling schemes (uniform, cyclic, acyclic) in C++. It shows how to associate these time samplings with different geometric objects and write animated samples.

```cpp
#include <Alembic/AbcGeom/All.h>
#include <Alembic/AbcCoreOgawa/All.h>

using namespace Alembic::AbcGeom;
using namespace Alembic::AbcCoreAbstract;

int main() {
    OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "timeSampling.abc");

    // Index 0 is reserved for identity (1 fps, start at 0)

    // Create uniform time sampling (constant interval)
    // 24 fps, starting at frame 1 (1/24 second)
    TimeSampling uniformTS(1.0/24.0, 1.0/24.0);
    uint32_t uniformIndex = archive.addTimeSampling(uniformTS);

    // Create cyclic time sampling (repeating pattern)
    std::vector<chrono_t> cyclicTimes = {0.0, 0.5, 1.0};  // 3 samples per cycle
    TimeSamplingType cyclicType(3, 2.0);  // 3 samples, 2 second cycle
    TimeSampling cyclicTS(cyclicType, cyclicTimes);
    uint32_t cyclicIndex = archive.addTimeSampling(cyclicTS);

    // Create acyclic time sampling (irregular intervals)
    std::vector<chrono_t> acyclicTimes = {0.0, 0.1, 0.15, 0.5, 1.0, 2.0};
    TimeSamplingType acyclicType(TimeSamplingType::kAcyclic);
    TimeSampling acyclicTS(acyclicType, acyclicTimes);
    uint32_t acyclicIndex = archive.addTimeSampling(acyclicTS);

    std::cout << "Uniform index: " << uniformIndex << std::endl;
    std::cout << "Cyclic index: " << cyclicIndex << std::endl;
    std::cout << "Acyclic index: " << acyclicIndex << std::endl;

    // Use different time sampling for different objects
    OXform uniformXform(archive.getTop(), "uniform");
    uniformXform.getSchema().setTimeSampling(uniformIndex);

    OXform acyclicXform(archive.getTop(), "acyclic");
    acyclicXform.getSchema().setTimeSampling(acyclicIndex);

    // Write samples
    XformSample sample;
    XformOp transOp(kTranslateOperation);

    for (int i = 0; i < 48; ++i) {
        sample.addOp(transOp, V3d(i, 0, 0));
        uniformXform.getSchema().set(sample);
    }

    // For acyclic, write exactly the number of time samples
    for (size_t i = 0; i < acyclicTimes.size(); ++i) {
        sample.addOp(transOp, V3d(0, i * 10, 0));
        acyclicXform.getSchema().set(sample);
    }

    return 0;
}
```

### Write Hierarchical Transform Data with OXform

Demonstrates writing hierarchical transform data to an Alembic archive. It supports translation, rotation, scale, and matrix operations, allowing for animated transformations. Requires Alembic's Geom and CoreOgawa libraries.

```cpp
#include <Alembic/AbcGeom/All.h>
#include <Alembic/AbcCoreOgawa/All.h>

using namespace Alembic::AbcGeom;

int main() {
    OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), "transform.abc");

    // Create time sampling at 24 fps
    AbcA::TimeSamplingPtr ts(new AbcA::TimeSampling(1.0/24.0, 0.0));

    // Create transform hierarchy
    OXform rootXform(archive.getTop(), "root", ts);
    OXform childXform(rootXform, "child", ts);

    // Define transform operations
    XformOp translateOp(kTranslateOperation, kTranslateHint);
    XformOp rotateOp(kRotateOperation, kRotateHint);
    XformOp scaleOp(kScaleOperation, kScaleHint);

    // Animate root transform
    for (int frame = 0; frame < 48; ++frame) {
        XformSample sample;

        // Add operations in order (applied right to left)
        sample.addOp(translateOp, V3d(0.0, frame * 0.5, 0.0));   // Y translation
        sample.addOp(rotateOp, V3d(0.0, 1.0, 0.0), frame * 7.5); // Y rotation
        sample.addOp(scaleOp, V3d(1.0, 1.0, 1.0));               // Uniform scale

        // Set child bounds for proper bounding box computation
        Box3d childBounds(V3d(-1,-1,-1), V3d(1,1,1));
        rootXform.getSchema().getChildBoundsProperty().set(childBounds);

        rootXform.getSchema().set(sample);
    }

    // Child with matrix operation (for complex transforms)
    XformSample childSample;
    M44d matrix;
    matrix.setTranslation(V3d(5.0, 0.0, 0.0));
    matrix.setScale(V3d(0.5, 0.5, 0.5));

    XformOp matrixOp(kMatrixOperation, kMatrixHint);
    childSample.addOp(matrixOp, matrix);
    childSample.setInheritsXforms(true);  // Inherit parent transform
    childXform.getSchema().set(childSample);

    std::cout << "Root samples: " << rootXform.getSchema().getNumSamples() << std::endl;
    return 0;
}
```

### Read and Write Alembic Archives with Python Bindings (PyAlembic)

Provides Python code examples for writing an Alembic archive with transform and mesh data, and subsequently reading it back. It demonstrates traversing the archive hierarchy and accessing object properties.

```python
import alembic
from alembic import Abc, AbcGeom
from imath import V3f, V2f, Box3d

# Writing an archive
archive = Abc.OArchive("python_output.abc")
root = archive.getTop()

# Create transform hierarchy
xform = AbcGeom.OXform(root, "myXform")
xform_schema = xform.getSchema()

# Create animated xform sample
xform_sample = AbcGeom.XformSample()
xform_sample.setTranslation(V3f(0, 0, 0))
xform_sample.setScale(V3f(1, 1, 1))
xform_schema.set(xform_sample)

# Create mesh
mesh = AbcGeom.OPolyMesh(xform, "myMesh")
mesh_schema = mesh.getSchema()

# Define triangle
positions = [V3f(0, 0, 0), V3f(1, 0, 0), V3f(0.5, 1, 0)]
indices = [0, 1, 2]
counts = [3]

mesh_sample = AbcGeom.OPolyMeshSchemaSample(positions, indices, counts)
mesh_schema.set(mesh_sample)

# Close archive (or let it go out of scope)
del archive

# Reading an archive
archive = Abc.IArchive("python_output.abc")
root = archive.getTop()

print(f"Archive: {archive.getName()}")
print(f"Children: {root.getNumChildren()}")

# Traverse hierarchy
def traverse(obj, depth=0):
    indent = "  " * depth
    print(f"{indent}{obj.getName()}")

    # Check object type
    if AbcGeom.IXform.matches(obj.getHeader()):
        xform = AbcGeom.IXform(obj)
        schema = xform.getSchema()
        sample = schema.getValue()
        print(f"{indent}  Matrix: {sample.getMatrix()}")

    if AbcGeom.IPolyMesh.matches(obj.getHeader()):
        mesh = AbcGeom.IPolyMesh(obj)
        schema = mesh.getSchema()
        sample = schema.getValue()
        print(f"{indent}  Vertices: {len(sample.getPositions())}")

    for i in range(obj.getNumChildren()):
        child = Abc.IObject(obj, obj.getChildHeader(i).getName())
        traverse(child, depth + 1)

traverse(root)
```

### Define Executable with Multiple Sources and Link Library (C++)

This snippet defines an executable target named 'AbcMaterial_MaterialFlattenTest' using two source files: 'MaterialFlattenTest.cpp' and 'PrintMaterial.cpp'. It links the executable against the 'Alembic' library and registers it as a test named 'AbcMaterial_MaterialFlatten_TEST'.

```cmake
ADD_EXECUTABLE(AbcMaterial_MaterialFlattenTest
               MaterialFlattenTest.cpp PrintMaterial.cpp
               )
TARGET_LINK_LIBRARIES(AbcMaterial_MaterialFlattenTest Alembic)
ADD_TEST(AbcMaterial_MaterialFlatten_TEST AbcMaterial_MaterialFlattenTest)
```

### Install Executable (CMake)

This CMake command installs the 'abcdiff' target (the executable built previously) into the 'bin' directory on the target system. This ensures that the compiled executable is placed in a standard location for user access after the build and installation process.

```cmake
INSTALL(TARGETS abcdiff DESTINATION bin)
```

### Install Executable (CMake)

Installs the 'abcls' target to the 'bin' directory relative to the installation prefix. This command is used to make the built executable available after the installation step of the build process.

```cmake
INSTALL(TARGETS abcls DESTINATION bin)
```

### Define Executable and Link Library (C++)

This snippet defines an executable target named 'AbcMaterial_WriteMaterialTest' using the 'WriteMaterial.cpp' source file. It then links this executable against the 'Alembic' library, making its functionalities available. Finally, it registers the executable as a test named 'AbcMaterial_WriteMaterial_TEST'.

```cmake
ADD_EXECUTABLE(AbcMaterial_WriteMaterialTest
               WriteMaterial.cpp
               )
TARGET_LINK_LIBRARIES(AbcMaterial_WriteMaterialTest Alembic)
ADD_TEST(AbcMaterial_WriteMaterial_TEST AbcMaterial_WriteMaterialTest)
```

### Configuration Option Display Macro (CMake)

This CMake macro, `info_cfg_option`, is used to format and display the status of various configuration settings. It takes an option name as input and appends its value to a configuration message string.

```cmake
SET(_config_msg "\n   * Alembic Configuration              ===")
MACRO(info_cfg_option
    _setting)
    SET(_msg "   * ${_setting}")
    STRING(LENGTH "${_msg}" _len)
    WHILE("40" GREATER "${_len}")
        SET(_msg "${_msg} ")
        MATH(EXPR _len "${_len} + 1")
    ENDWHILE()
    SET(_config_msg "${_config_msg}\n${_msg}${${_setting}}")
ENDMACRO()

info_cfg_option(USE_ARNOLD)
info_cfg_option(USE_BINARIES)
info_cfg_option(USE_EXAMPLES)
info_cfg_option(USE_HDF5)
info_cfg_option(USE_MAYA)
info_cfg_option(USE_PRMAN)
info_cfg_option(USE_PYALEMBIC)
info_cfg_option(USE_STATIC_BOOST)
info_cfg_option(USE_STATIC_HDF5)
info_cfg_option(USE_TESTS)
info_cfg_option(ALEMBIC_SHARED_LIBS)
info_cfg_option(ALEMBIC_DEBUG_WARNINGS_AS_ERRORS)
info_cfg_option(PYALEMBIC_PYTHON_MAJOR)
info_cfg_option(DOCS_PATH)
MESSAGE("${_config_msg}")
```