# =============================================================================
# VESTA — LA FAILLE DE LA FORGE (fond vidéo scrubbé au scroll)
# =============================================================================
# Deux berges de basalte, une fracture qui s'élargit le long du parcours,
# un lit de lave qui coule en contrebas. La caméra suit la faille :
# scroller le site = descendre la fracture.
#
# UTILISATION (PowerShell, Blender fermé) :
#   & "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b -P faille_blender.py
#
# Sortie :  C:\Users\natha\Documents\VESTA\faille\
#   ├── frames\####.png            (480 images)
#   └── faille_scrub.mp4           (assemblé automatiquement si ffmpeg est là,
#                                    encodage ALL-INTRA : chaque frame est une
#                                    keyframe -> currentTime répond au pixel)
#
# MODE TEST : passe TEST = True ci-dessous (72 frames, 50 %) ~2 min,
# pour valider le look avant le rendu complet (~15-25 min sur RTX 4070).
# =============================================================================
import bpy
import bmesh
import math
import os
import random
import subprocess

# ----------------------------- RÉGLAGES --------------------------------------
TEST = False                     # True = aperçu rapide 72 frames à 50 %
SORTIE = r"C:\Users\natha\Documents\VESTA\faille"
FRAMES = 72 if TEST else 480     # 480 f @ 24 fps = 20 s de course de scroll
RES = (1920, 1080)
LONGUEUR = 150.0                 # longueur du canyon (m)
LARGEUR_BERGE = 14.0
random.seed(7)

os.makedirs(os.path.join(SORTIE, "frames"), exist_ok=True)

# ----------------------------- SCÈNE VIERGE ----------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
# Blender 5.x : EEVEE Next est devenu l'EEVEE standard
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 50 if TEST else 100
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24
try:
    scene.eevee.taa_render_samples = 24
except Exception:
    pass
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("Void")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.003, 0.002, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0


def largeur_faille(y):
    """La fracture s'ouvre le long du parcours : mince au départ, béante au bout."""
    t = (y + LONGUEUR / 2) / LONGUEUR                # 0 -> 1 le long du canyon
    base = 0.14 + 2.1 * (t ** 1.4)                   # ouverture progressive
    serpent = math.sin(y * 0.16) * 0.5 + math.sin(y * 0.047 + 1.7) * 0.9
    return base, serpent                             # (demi-largeur, méandre du centre)


# ----------------------------- LES BERGES ------------------------------------
def berge(cote):  # cote = -1 (gauche) ou +1 (droite)
    mesh = bpy.data.meshes.new("Berge")
    obj = bpy.data.objects.new("Berge" + ("G" if cote < 0 else "D"), mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    NX, NY = 42, 560
    grille = {}
    for j in range(NY + 1):
        y = -LONGUEUR / 2 + LONGUEUR * j / NY
        demi, serpent = largeur_faille(y)
        bord = serpent + cote * demi
        # bord déchiqueté : le trait de fracture n'est jamais net
        bord += cote * (abs(math.sin(y * 2.3 + cote)) * 0.22 + abs(math.sin(y * 7.1)) * 0.09)
        for i in range(NX + 1):
            u = i / NX
            x = bord + cote * u * LARGEUR_BERGE
            # relief rocheux : plusieurs octaves de bruit sinusoïdal déphasé
            z = (math.sin(x * 0.7 + y * 0.31) * 0.5
                 + math.sin(x * 1.9 - y * 0.9 + 2.0) * 0.24
                 + math.sin(x * 4.7 + y * 2.3) * 0.1
                 + random.uniform(-0.035, 0.035))
            # les lèvres de la faille se soulèvent légèrement (bourrelet)
            z += max(0.0, 0.5 - u) * 0.55
            grille[(i, j)] = bm.verts.new((x, y, z))
    for j in range(NY):
        for i in range(NX):
            bm.faces.new((grille[(i, j)], grille[(i + 1, j)],
                          grille[(i + 1, j + 1)], grille[(i, j + 1)]))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    # épaisseur vers le bas : les parois internes du canyon
    solid = obj.modifiers.new("S", "SOLIDIFY")
    solid.thickness = 3.4
    solid.offset = -1.0
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def materiau_basalte():
    m = bpy.data.materials.new("Basalte")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.86
    bsdf.inputs["Base Color"].default_value = (0.028, 0.022, 0.018, 1)
    # variation rocheuse + veines chaudes près du bord (la roche chauffée)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (0.018, 0.014, 0.012, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.075, 0.055, 0.042, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.55
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


basalte = materiau_basalte()
for cote in (-1, 1):
    b = berge(cote)
    b.data.materials.append(basalte)

# ----------------------------- LA LAVE ---------------------------------------
lave_mesh = bpy.data.meshes.new("Lave")
lave = bpy.data.objects.new("Lave", lave_mesh)
bpy.context.collection.objects.link(lave)
bm = bmesh.new()
NY = 560
gauche, droite = [], []
for j in range(NY + 1):
    y = -LONGUEUR / 2 + LONGUEUR * j / NY
    demi, serpent = largeur_faille(y)
    gauche.append(bm.verts.new((serpent - demi - 0.5, y, -2.6)))
    droite.append(bm.verts.new((serpent + demi + 0.5, y, -2.6)))
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
# l'écoulement : un bruit qui glisse le long de la faille avec le temps
mapping = nt.nodes.new("ShaderNodeMapping")
coords = nt.nodes.new("ShaderNodeTexCoord")
flux = nt.nodes.new("ShaderNodeTexNoise")
flux.inputs["Scale"].default_value = 1.1
flux.inputs["Detail"].default_value = 9.0
flux.inputs["Roughness"].default_value = 0.62
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.34
ramp.color_ramp.elements[0].color = (0.28, 0.012, 0.001, 1)   # croûte sombre
e1 = ramp.color_ramp.elements.new(0.58)
e1.color = (1.0, 0.16, 0.01, 1)                               # rouge lave
e2 = ramp.color_ramp.elements.new(0.8)
e2.color = (1.0, 0.62, 0.12, 1)                               # or en fusion
ramp.color_ramp.elements[-1].color = (1.0, 0.92, 0.55, 1)     # cœur blanc
nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])
nt.links.new(mapping.outputs["Vector"], flux.inputs["Vector"])
nt.links.new(flux.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], emis.inputs["Color"])
emis.inputs["Strength"].default_value = 9.0
nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
lave.data.materials.append(mlave)

# la lave coule : le mapping glisse en Y au fil des frames
mapping.inputs["Location"].default_value[1] = 0.0
mapping.inputs["Location"].keyframe_insert("default_value", index=1, frame=1)
mapping.inputs["Location"].default_value[1] = -22.0
mapping.inputs["Location"].keyframe_insert("default_value", index=1, frame=FRAMES)

# lumière volumique de la faille : une rangée de spots orange
for k in range(10):
    y = -LONGUEUR / 2 + LONGUEUR * (k + 0.5) / 10
    demi, serpent = largeur_faille(y)
    lum = bpy.data.lights.new("L" + str(k), "AREA")
    lum.energy = 900 + 500 * (k / 9)
    lum.color = (1.0, 0.38, 0.1)
    lum.size = 3.5
    ol = bpy.data.objects.new("Lum" + str(k), lum)
    ol.location = (serpent, y, -0.8)
    ol.rotation_euler = (0, 0, 0)
    bpy.context.collection.objects.link(ol)

# ----------------------------- LA CAMÉRA -------------------------------------
cam = bpy.data.cameras.new("Cam")
cam.lens = 24
ocam = bpy.data.objects.new("Camera", cam)
bpy.context.collection.objects.link(ocam)
scene.camera = ocam

DEB, FIN = -LONGUEUR / 2 + 8, LONGUEUR / 2 - 10
PAS = 8
for s in range(PAS + 1):
    f = 1 + (FRAMES - 1) * s / PAS
    t = s / PAS
    y = DEB + (FIN - DEB) * t
    demi, serpent = largeur_faille(y)
    # la caméra survole la faille, avec un léger balancement organique
    ocam.location = (serpent + math.sin(t * 6.28 * 1.5) * 0.9,
                     y,
                     4.6 + math.sin(t * 6.28 * 2.2 + 1) * 0.35)
    # regard : vers l'avant et vers le bas, suivant le méandre
    demi2, serp2 = largeur_faille(min(FIN, y + 9))
    dx = (serp2 - ocam.location[0])
    ocam.rotation_euler = (math.radians(64), 0, math.atan2(-dx, 9) * 0.9)
    ocam.keyframe_insert("location", frame=f)
    ocam.keyframe_insert("rotation_euler", frame=f)

# interpolation douce sur toute la course (API 4.x ET 5.x "layered actions")
def toutes_fcurves(action):
    try:
        return list(action.fcurves)                    # Blender <= 4.x
    except AttributeError:
        fcs = []                                       # Blender 5.x : actions en couches
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
    print("(lissage caméra ignoré :", e, "— l'interpolation par défaut est déjà Bézier)")

# ----------------------------- LE GLOW (compositor) --------------------------
# Optionnel par construction : si l'API compositor de cette version résiste,
# on rend sans glow (la lave émissive brille déjà) plutôt que d'échouer.
try:
    ct = None
    if hasattr(scene, "node_tree"):
        try:
            scene.use_nodes = True
            ct = scene.node_tree
        except Exception:
            ct = None
    if ct is None:
        # Blender 5.x : le compositor est un groupe de nœuds assigné à la scène
        ct = bpy.data.node_groups.new("VestaCompo", "CompositorNodeTree")
        assigne = False
        for prop in ("compositing_node_group", "compositor_node_tree"):
            if hasattr(scene, prop):
                setattr(scene, prop, ct)
                assigne = True
                break
        if not assigne:
            raise RuntimeError("aucune propriété compositor connue sur Scene")
    for n in list(ct.nodes):
        ct.nodes.remove(n)
    rl = ct.nodes.new("CompositorNodeRLayers")
    glare = ct.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    for attr, val in (("quality", "MEDIUM"), ("threshold", 0.85), ("size", 8)):
        try:
            setattr(glare, attr, val)
        except Exception:
            pass
    try:
        comp = ct.nodes.new("CompositorNodeComposite")
    except Exception:
        # groupe 5.x : sortie via Group Output + socket d'interface
        ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        comp = ct.nodes.new("NodeGroupOutput")
    ct.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ct.links.new(glare.outputs["Image"], comp.inputs[0])
    print(">>> Glow compositor : ACTIF")
except Exception as e:
    print(">>> Glow compositor ignoré (", e, ") — rendu sans post-traitement.")

# ----------------------------- RENDU -----------------------------------------
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(SORTIE, "frames", "")
print(">>> Rendu de", FRAMES, "frames vers", scene.render.filepath)
bpy.ops.render.render(animation=True)

# ----------------------------- ASSEMBLAGE SCRUB-READY ------------------------
# ALL-INTRA (-g 1) : chaque frame est une keyframe -> video.currentTime
# répond instantanément au scroll, dans les deux sens, sans saccade.
mp4 = os.path.join(SORTIE, "faille_scrub.mp4")
cmd = ["ffmpeg", "-y", "-framerate", "24",
       "-i", os.path.join(SORTIE, "frames", "%04d.png"),
       "-c:v", "libx264", "-g", "1", "-crf", "23", "-preset", "slow",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4]
try:
    subprocess.run(cmd, check=True)
    print(">>> TERMINÉ :", mp4)
except Exception as e:
    print(">>> Frames rendues. Assemble ensuite avec :\n   " + " ".join(cmd))
