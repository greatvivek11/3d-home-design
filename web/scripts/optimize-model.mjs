import { createHash } from 'node:crypto'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions'
import { MeshoptEncoder } from 'meshoptimizer/encoder'
import { MeshoptDecoder } from 'meshoptimizer/decoder'

function fingerprint(document) {
  const bytes = (array) => {
    if (!array) throw new Error('A geometry accessor has no data')
    return createHash('sha256').update(Buffer.from(array.buffer, array.byteOffset, array.byteLength)).digest('hex')
  }
  const root = document.getRoot()
  const meshes = root.listMeshes().map((mesh) => ({
    name: mesh.getName(),
    primitives: mesh.listPrimitives().map((primitive) => {
      const indices = primitive.getIndices()?.getArray()
      if (!indices || primitive.getMode() !== 4) throw new Error('Expected indexed triangle geometry')
      const triangles = new Uint32Array(indices.length)
      for (let i = 0; i < indices.length; i += 3) {
        const first = indices[i] < indices[i + 1] ? (indices[i] < indices[i + 2] ? 0 : 2) : (indices[i + 1] < indices[i + 2] ? 1 : 2)
        for (let j = 0; j < 3; j++) triangles[i + j] = indices[i + (first + j) % 3]
      }
      return {
        mode: primitive.getMode(), indices: bytes(triangles),
        attributes: primitive.listSemantics().sort().map((name) => [name, bytes(primitive.getAttribute(name).getArray())]),
        material: primitive.getMaterial()?.getName(),
      }
    }),
  }))
  const nodes = root.listNodes().map((node) => ({
    name: node.getName(), matrix: [...node.getMatrix()], extras: node.getExtras(),
    mesh: node.getMesh()?.getName(), children: node.listChildren().map((child) => child.getName()),
  }))
  return createHash('sha256').update(JSON.stringify({ meshes, nodes })).digest('hex')
}

const argument = process.argv[2]
if (!argument) throw new Error('Pass a freshly exported GLB path. The Blender web exporter runs this step automatically.')
const path = resolve(argument)
await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready])
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder,
})
const input = await readFile(path)
const document = await io.readBinary(input)
const before = fingerprint(document)
// No quantization, filters, simplification or reordering: preserve every attribute bit.
document.createExtension(EXTMeshoptCompression).setRequired(true)
  .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE })
const output = await io.writeBinary(document)
if (fingerprint(await io.readBinary(output)) !== before) throw new Error('Compression changed geometry, transforms or picking identities')
if (output.byteLength >= input.byteLength) throw new Error('Meshopt compression did not reduce the model size')
const pending = `${path}.meshopt.pending`
await writeFile(pending, output)
await rename(pending, path)
console.log(`MODEL_COMPRESSION_SUCCESS ${JSON.stringify({
  input_bytes: input.byteLength, output_bytes: output.byteLength,
  reduction_percent: Number((100 * (1 - output.byteLength / input.byteLength)).toFixed(1)),
  geometry_sha256: before, method: 'lossless_meshopt',
})}`)
