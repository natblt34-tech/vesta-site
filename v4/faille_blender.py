# =============================================================================
# VESTA — LA FAILLE DE LA FORGE, v2 PHOTORÉALISTE
# =============================================================================
# Cycles GPU (illumination globale : la lave éclaire réellement les parois),
# textures PBR scannées Poly Haven (téléchargées automatiquement),
# géométrie fractale multi-octaves (fini les ondes synthétiques).
#
# UTILISATION :
#   & "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b -P faille_blender.py
#
# TEMPS (RTX 4070) : TEST = True  -> ~8-15 min (72 frames, 50 %, 64 samples)
#                    TEST = False -> ~2-4 h    (480 frames, 1080p, 128 samples)
# Sortie : C:\Users\natha\Documents\VESTA\faille\faille_scrub.mp4 (all-intra)
# =============================================================================
import bpy
import bmesh
import math
import os
import json
import random
import subprocess
import urllib.request

TEST = True
SORTIE = r"C:\Users\natha\Documents\VESTA\faille"
FRAMES = 72 if TEST else 480
RES = (1920, 1080)
SAMPLES = 64 if TEST else 128
LONGUEUR = 150.0
LARGEUR_BERGE = 14.0
random.seed(7)
os.makedirs(os.path.join(SORTIE, "frames"), exist_ok=True)
os.makedirs(os.path.join(SORTIE, "textures"), exist_ok=True)

# ----------------------------------------------------------------------------
# TEXTURES PBR (Poly Haven) — plusieurs candidats, le premier qui répond gagne
# ----------------------------------------------------------------------------
CANDIDATS = ["rock_wall_08", "rock_wall_10", "cliff_side", "rock_face_03",
             "rock_boulder_cracked", "rock_wall_02"]


def telecharge(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 10000:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "vesta-forge/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def resoud_pbr():
    """Retourne {diff, nor, rough, disp} de la première falaise Poly Haven dispo."""
    for slug in CANDIDATS:
        try:
            req = urllib.request.Request("https://api.polyhaven.com/files/" + slug,
                                         headers={"User-Agent": "vesta-forge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            trouve = {}
            for cle, motifs in (("diff", ("diff",)), ("nor", ("nor_gl",)),
                                ("rough", ("rough",)), ("disp", ("disp", "displacement"))):
                for k, v in data.items():
                    if any(m in k.lower() for m in motifs) and isinstance(v, dict) and "2k" in v:
                        fmts = v["2k"]
                        fmt = "jpg" if "jpg" in fmts else ("png" if "png" in fmts else None)
                        if fmt:
                            url = fmts[fmt]["url"]
                            dest = os.path.join(SORTIE, "textures",
                                                slug + "_" + cle + "." + fmt)
                            trouve[cle] = telecharge(url, dest)
                        break
            if "diff" in trouve and "nor" in trouve:
                print(">>> Textures PBR :", slug, "-", list(trouve.keys()))
                return trouve
        except Exception as e:
            print("   (", slug, "indisponible :", e, ")")
    print(">>> Poly Haven inaccessible : repli sur un shader procédural.")
    return {}


PBR = resoud_pbr()

# ----------------------------------------------------------------------------
# SCÈNE + CYCLES GPU
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 50 if TEST else 100
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for mode in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = mode
            break
        except Exception:
            continue
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
    print(">>> Cycles GPU :", prefs.compute_device_type)
except Exception as e:
    print(">>> GPU non configuré (", e, ") : rendu CPU (plus lent).")
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
except Exception:
    pass

scene.world = bpy.data.worlds.new("Void")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.0012, 0.0008, 0.0006, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ----------------------------------------------------------------------------
# BRUIT FRACTAL (le chaos minéral, pas des ondes)
# ----------------------------------------------------------------------------
def _hash(ix, iy):
    h = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def _lisse(t):
    return t * t * (3 - 2 * t)


def bruit(x, y):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    a, b = _hash(ix, iy), _hash(ix + 1, iy)
    c, d = _hash(ix, iy + 1), _hash(ix + 1, iy + 1)
    ux, uy = _lisse(fx), _lisse(fy)
    return (a * (1 - ux) + b * ux) * (1 - uy) + (c * (1 - ux) + d * ux) * uy


def fractal(x, y, octaves=5, lac=2.1, gain=0.52):
    v, amp, f = 0.0, 1.0, 1.0
    for _ in range(octaves):
        v += (bruit(x * f, y * f) - 0.5) * 2 * amp
        amp *= gain
        f *= lac
    return v


def largeur_faille(y):
    t = (y + LONGUEUR / 2) / LONGUEUR
    base = 0.16 + 2.3 * (t ** 1.4)
    serpent = math.sin(y * 0.14) * 0.6 + math.sin(y * 0.043 + 1.7) * 1.1
    return base, serpent


# ----------------------------------------------------------------------------
# LES BERGES (géométrie fractale + UV pour les textures scannées)
# ----------------------------------------------------------------------------
def berge(cote):
    mesh = bpy.data.meshes.new("Berge")
    obj = bpy.data.objects.new("Berge" + ("G" if cote < 0 else "D"), mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    NX, NY = 56, 720
    grille = {}
    for j in range(NY + 1):
        y = -LONGUEUR / 2 + LONGUEUR * j / NY
        demi, serpent = largeur_faille(y)
        bord = serpent + cote * demi
        bord += cote * (abs(fractal(3.0, y * 0.9)) * 0.5 + abs(fractal(9.0, y * 3.1)) * 0.14)
        for i in range(NX + 1):
            u = i / NX
            x = bord + cote * u * LARGEUR_BERGE
            z = (fractal(x * 0.16, y * 0.16) * 1.5
                 + fractal(x * 0.55, y * 0.55) * 0.55
                 + fractal(x * 2.1, y * 2.1) * 0.16)
            z += max(0.0, 0.42 - u) * (0.7 + fractal(x, y * 0.4) * 0.35)
            grille[(i, j)] = bm.verts.new((x, y, z))
    for j in range(NY):
        for i in range(NX):
            f = bm.faces.new((grille[(i, j)], grille[(i + 1, j)],
                              grille[(i + 1, j + 1)], grille[(i, j + 1)]))
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co.x * 0.11, co.y * 0.11)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    solid = obj.modifiers.new("S", "SOLIDIFY")
    solid.thickness = 4.0
    solid.offset = -1.0
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def materiau_roche():
    m = bpy.data.materials.new("Roche")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if PBR:
        def img(chemin, non_couleur):
            image = bpy.data.images.load(chemin)
            if non_couleur:
                image.colorspace_settings.name = "Non-Color"
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = image
            return n
        tdiff = img(PBR["diff"], False)
        teinte = nt.nodes.new("ShaderNodeMixRGB")
        teinte.blend_type = "MULTIPLY"
        teinte.inputs["Fac"].default_value = 1.0
        teinte.inputs["Color2"].default_value = (0.3, 0.23, 0.19, 1)
        nt.links.new(tdiff.outputs["Color"], teinte.inputs["Color1"])
        nt.links.new(teinte.outputs["Color"], bsdf.inputs["Base Color"])
        tnor = img(PBR["nor"], True)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 1.4
        nt.links.new(tnor.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        if "rough" in PBR:
            trough = img(PBR["rough"], True)
            nt.links.new(trough.outputs["Color"], bsdf.inputs["Roughness"])
        else:
            bsdf.inputs["Roughness"].default_value = 0.88
    else:
        bsdf.inputs["Base Color"].default_value = (0.05, 0.04, 0.033, 1)
        bsdf.inputs["Roughness"].default_value = 0.9
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 14.0
        noise.inputs["Detail"].default_value = 12.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.7
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


roche = materiau_roche()
berges = []
for cote in (-1, 1):
    b = berge(cote)
    b.data.materials.append(roche)
    berges.append(b)

if "disp" in PBR:
    imgd = bpy.data.images.load(PBR["disp"])
    tex = bpy.data.textures.new("Disp", "IMAGE")
    tex.image = imgd
    for b in berges:
        d = b.modifiers.new("D", "DISPLACE")
        d.texture = tex
        d.texture_coords = "UV"
        d.strength = 0.5
        d.mid_level = 0.5

# ----------------------------------------------------------------------------
# LA LAVE (émissive : c'est ELLE la source de lumière, Cycles fait le reste)
# ----------------------------------------------------------------------------
lave_mesh = bpy.data.meshes.new("Lave")
lave = bpy.data.objects.new("Lave", lave_mesh)
bpy.context.collection.objects.link(lave)
bm = bmesh.new()
NY = 720
gauche, droite = [], []
for j in range(NY + 1):
    y = -LONGUEUR / 2 + LONGUEUR * j / NY
    demi, serpent = largeur_faille(y)
    zl = -2.8 + fractal(1.0, y * 0.5) * 0.3
    gauche.append(bm.verts.new((serpent - demi - 0.7, y, zl)))
    droite.append(bm.verts.new((serpent + demi + 0.7, y, zl)))
for j in range(NY):
    bm.faces.new((gauche[j], droite[j], droite[j + 1], gauche[j + 1]))
bm.to_mesh(lave_mesh)
bm.free()

mlave = bpy.data.materials.new("Lave")
mlave.use_nodes = True
nt = mlave.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
out = nt.nodes["Material Output"]
emis = nt.nodes.new("ShaderNodeEmission")
mapping = nt.nodes.new("ShaderNodeMapping")
coords = nt.nodes.new("ShaderNodeTexCoord")
flux = nt.nodes.new("ShaderNodeTexNoise")
flux.inputs["Scale"].default_value = 0.9
flux.inputs["Detail"].default_value = 14.0
flux.inputs["Roughness"].default_value = 0.68
try:
    flux.inputs["Distortion"].default_value = 0.9
except Exception:
    pass
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.36
ramp.color_ramp.elements[0].color = (0.02, 0.002, 0.0, 1)
e1 = ramp.color_ramp.elements.new(0.5)
e1.color = (0.62, 0.03, 0.001, 1)
e2 = ramp.color_ramp.elements.new(0.68)
e2.color = (1.0, 0.2, 0.012, 1)
e3 = ramp.color_ramp.elements.new(0.86)
e3.color = (1.0, 0.66, 0.14, 1)
ramp.color_ramp.elements[-1].color = (1.0, 0.94, 0.6, 1)
nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
nt.links.new(mapping.outputs["Vector"], flux.inputs["Vector"])
nt.links.new(flux.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], emis.inputs["Color"])
emis.inputs["Strength"].default_value = 40.0
nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
lave.data.materials.append(mlave)

mapping.inputs["Location"].default_value[1] = 0.0
mapping.inputs["Location"].keyframe_insert("default_value", index=1, frame=1)
mapping.inputs["Location"].default_value[1] = -24.0
mapping.inputs["Location"].keyframe_insert("default_value", index=1, frame=FRAMES)

# ----------------------------------------------------------------------------
# LA CAMÉRA — plus basse, plus rasante : la texture remplit le cadre
# ----------------------------------------------------------------------------
cam = bpy.data.cameras.new("Cam")
cam.lens = 30
ocam = bpy.data.objects.new("Camera", cam)
bpy.context.collection.objects.link(ocam)
scene.camera = ocam

DEB, FIN = -LONGUEUR / 2 + 8, LONGUEUR / 2 - 12
PAS = 8
for s in range(PAS + 1):
    f = 1 + (FRAMES - 1) * s / PAS
    t = s / PAS
    y = DEB + (FIN - DEB) * t
    demi, serpent = largeur_faille(y)
    ocam.location = (serpent + math.sin(t * 6.28 * 1.5) * 0.55,
                     y,
                     2.9 + math.sin(t * 6.28 * 2.2 + 1) * 0.22)
    demi2, serp2 = largeur_faille(min(FIN, y + 9))
    dx = (serp2 - ocam.location[0])
    ocam.rotation_euler = (math.radians(73), 0, math.atan2(-dx, 9) * 0.9)
    ocam.keyframe_insert("location", frame=f)
    ocam.keyframe_insert("rotation_euler", frame=f)


def toutes_fcurves(action):
    try:
        return list(action.fcurves)
    except AttributeError:
        fcs = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    fcs.extend(bag.fcurves)
        return fcs


try:
    if ocam.animation_data and ocam.animation_data.action:
        for fc in toutes_fcurves(ocam.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "AUTO"
except Exception as e:
    print("(lissage caméra ignoré :", e, ")")

# ----------------------------------------------------------------------------
# GLOW compositor — optionnel, jamais bloquant
# ----------------------------------------------------------------------------
try:
    ct = None
    if hasattr(scene, "node_tree"):
        try:
            scene.use_nodes = True
            ct = scene.node_tree
        except Exception:
            ct = None
    if ct is None:
        ct = bpy.data.node_groups.new("VestaCompo", "CompositorNodeTree")
        for prop in ("compositing_node_group", "compositor_node_tree"):
            if hasattr(scene, prop):
                setattr(scene, prop, ct)
                break
        else:
            raise RuntimeError("propriété compositor introuvable")
    for n in list(ct.nodes):
        ct.nodes.remove(n)
    rl = ct.nodes.new("CompositorNodeRLayers")
    glare = ct.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    for attr, val in (("quality", "MEDIUM"), ("threshold", 0.9), ("size", 9)):
        try:
            setattr(glare, attr, val)
        except Exception:
            pass
    try:
        comp = ct.nodes.new("CompositorNodeComposite")
    except Exception:
        ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        comp = ct.nodes.new("NodeGroupOutput")
    ct.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ct.links.new(glare.outputs["Image"], comp.inputs[0])
    print(">>> Glow compositor : ACTIF")
except Exception as e:
    print(">>> Glow compositor ignoré (", e, ")")

# ----------------------------------------------------------------------------
# RENDU + ASSEMBLAGE SCRUB-READY
# ----------------------------------------------------------------------------
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(SORTIE, "frames", "")
print(">>> Rendu Cycles de", FRAMES, "frames…")
bpy.ops.render.render(animation=True)

mp4 = os.path.join(SORTIE, "faille_scrub.mp4")
cmd = ["ffmpeg", "-y", "-framerate", "24",
       "-i", os.path.join(SORTIE, "frames", "%04d.png"),
       "-c:v", "libx264", "-g", "1", "-crf", "23", "-preset", "slow",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4]
try:
    subprocess.run(cmd, check=True)
    print(">>> TERMINÉ :", mp4)
except Exception:
    print(">>> Frames rendues. Assemble avec :\n   " + " ".join(cmd))
