"""[cc] Fallback GLB generator for when Blender is unavailable or fails.
Produces a card.glb with correct geometry (front/back/edge meshes) and material
names (web_front, web_back, web_edge) matching the Three.js viewer contract.

Key details discovered through testing:
- Front face UVs must be U-flipped [(1,0),(0,0),(0,1),(1,1)] to avoid
  horizontal mirroring in the viewer.
- The web template app.js applies a 180-degree Z rotation to compensate for
  the coordinate system difference between programmatic geometry and Blender
  exports.
"""
import struct, json, shutil, argparse
from pathlib import Path


def generate_glb(project):
    """Create a minimal card GLB with correct UV mapping for the web viewer."""
    root = Path(project)
    # [cc] Card dimensions matching tarot proportions (2:3 aspect, thin edge)
    hw, hh, depth = 3.15, 4.5, 0.06

    # [cc] Front face: U-flipped UVs to fix horizontal mirror in the viewer.
    # Without the flip, text renders right-to-left (mirrored).
    front_v = [(-hw, -hh, depth), (hw, -hh, depth),
               (hw, hh, depth), (-hw, hh, depth)]
    front_n = [(0, 0, 1)] * 4
    front_uv = [(1, 0), (0, 0), (0, 1), (1, 1)]
    front_idx = [0, 1, 2, 0, 2, 3]

    # [cc] Back face: visible when card is flipped (viewed from -Z)
    back_v = [(hw, -hh, -depth), (-hw, -hh, -depth),
              (-hw, hh, -depth), (hw, hh, -depth)]
    back_n = [(0, 0, -1)] * 4
    back_uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    back_idx = [0, 1, 2, 0, 2, 3]

    # [cc] Edge strips: 4 quads connecting front and back faces
    edge_v, edge_n, edge_uv, edge_idx = [], [], [], []
    corners = [
        ((-hw, -hh), (0, -1, 0)), ((hw, -hh), (1, 0, 0)),
        ((hw, hh), (0, 1, 0)), ((-hw, hh), (-1, 0, 0)),
    ]
    vi = 0
    for i in range(4):
        (x1, y1), n = corners[i]
        (x2, y2), _ = corners[(i + 1) % 4]
        edge_v.extend([(x1, y1, depth), (x1, y1, -depth),
                       (x2, y2, depth), (x2, y2, -depth)])
        edge_n.extend([n] * 4)
        edge_uv.extend([(0, 0), (0, 1), (1, 0), (1, 1)])
        edge_idx.extend([vi, vi+1, vi+2, vi+1, vi+3, vi+2])
        vi += 4

    # [cc] Pack binary data
    def pack_vec3(vecs):
        return b''.join(struct.pack('<3f', *v) for v in vecs)

    def pack_vec2(vecs):
        return b''.join(struct.pack('<2f', *v) for v in vecs)

    def pack_idx(indices):
        return b''.join(struct.pack('<H', i) for i in indices)

    parts = []
    meshes = [(front_v, front_n, front_uv, front_idx),
              (back_v, back_n, back_uv, back_idx),
              (edge_v, edge_n, edge_uv, edge_idx)]
    for V, N, U, I in meshes:
        parts.extend([pack_vec3(V), pack_vec3(N), pack_vec2(U), pack_idx(I)])
    buf = b''.join(parts)
    while len(buf) % 4:
        buf += b'\x00'

    # [cc] Build glTF buffer views and accessors
    bvs, accs = [], []
    off = 0
    for V, N, U, I in meshes:
        for data, cnt, tp, tgt in [
            (V, len(V), 'VEC3', 34962), (N, len(N), 'VEC3', 34962),
            (U, len(U), 'VEC2', 34962), (I, len(I), 'SCALAR', 34963),
        ]:
            sz = cnt * (12 if tp == 'VEC3' else 8 if tp == 'VEC2' else 2)
            bvs.append({
                'buffer': 0, 'byteOffset': off,
                'byteLength': sz, 'target': tgt,
            })
            acc = {
                'bufferView': len(bvs) - 1,
                'componentType': 5126 if tp != 'SCALAR' else 5123,
                'count': cnt, 'type': tp,
            }
            if tp == 'VEC3' and data is V:
                acc['min'] = [min(v[i] for v in data) for i in range(3)]
                acc['max'] = [max(v[i] for v in data) for i in range(3)]
            accs.append(acc)
            off += sz

    gltf = {
        'asset': {'version': '2.0', 'generator': 'holo-card-studio-fallback'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [
            {'name': 'Card', 'children': [1, 2, 3]},
            {'name': 'Front', 'mesh': 0},
            {'name': 'Back', 'mesh': 1},
            {'name': 'Edge', 'mesh': 2},
        ],
        'meshes': [
            {'name': 'front', 'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2}, 'indices': 3, 'material': 0}]},
            {'name': 'back', 'primitives': [{'attributes': {'POSITION': 4, 'NORMAL': 5, 'TEXCOORD_0': 6}, 'indices': 7, 'material': 1}]},
            {'name': 'edge', 'primitives': [{'attributes': {'POSITION': 8, 'NORMAL': 9, 'TEXCOORD_0': 10}, 'indices': 11, 'material': 2}]},
        ],
        'materials': [
            {'name': 'web_front', 'pbrMetallicRoughness': {}},
            {'name': 'web_back', 'pbrMetallicRoughness': {}},
            {'name': 'web_edge', 'pbrMetallicRoughness': {}},
        ],
        'buffers': [{'byteLength': len(buf)}],
        'bufferViews': bvs,
        'accessors': accs,
    }

    # [cc] Encode GLB binary container
    jb = json.dumps(gltf, separators=(',', ':')).encode()
    while len(jb) % 4:
        jb += b' '
    total = 12 + 8 + len(jb) + 8 + len(buf)
    glb = struct.pack('<III', 0x46546C67, 2, total)
    glb += struct.pack('<II', len(jb), 0x4E4F534A) + jb
    glb += struct.pack('<II', len(buf), 0x004E4942) + buf

    dest = root / 'assets' / 'card.glb'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(glb)
    print(f'Fallback GLB generated: {dest} ({len(glb)} bytes)')
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description='Generate fallback card.glb without Blender')
    p.add_argument('project', help='Path to the card project directory')
    a = p.parse_args()
    generate_glb(a.project)
