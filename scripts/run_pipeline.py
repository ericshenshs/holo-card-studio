"""Build a user-owned Blender/Three.js project from prepared layered artwork."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys
from ensure_blender import ensure_blender
from validate_assets import validate
from generate_typography import create
# [cc] Import fallback GLB generator for when Blender fails (e.g. Blender 5.2 compositor API change)
from generate_glb import generate_glb

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--blender');p.add_argument('--skip-render',action='store_true');p.add_argument('--skip-npm',action='store_true');a=p.parse_args()
    root=Path(a.project).resolve();scripts=Path(__file__).resolve().parent;skill=scripts.parent
    config=root/'card-config.json'
    if not config.exists():raise FileNotFoundError('Write card-config.json from references/config.example.json first')
    if not (root/'assets'/'text.png').exists():create(root)
    validate(root)
    # [cc] Try Blender pipeline first; fall back to programmatic GLB if it fails
    blender_ok=False
    try:
        blender=ensure_blender(root,a.blender)
        cmd=[str(blender),'--background','--factory-startup','--python',str(scripts/'build_card.py'),'--',str(root)]
        if a.skip_render:cmd.append('--skip-render')
        subprocess.run(cmd,check=True)
        if not (root/'card.blend').exists():raise RuntimeError('Blender did not save card.blend')
        subprocess.run([str(blender),'--background','--python',str(scripts/'export_web.py'),'--',str(root)],check=True)
        if not (root/'web'/'assets'/'card.glb').exists():raise RuntimeError('GLB export failed')
        blender_ok=True
    except Exception as e:
        print(f'Blender pipeline failed: {e}')
        print('Falling back to programmatic GLB generation...')
        generate_glb(root)
        blender_ok=False
    web=root/'web';shutil.copytree(skill/'assets'/'web-template',web,dirs_exist_ok=True)
    # [cc] Copy GLB to web/assets (fallback GLB is already at root/assets/card.glb)
    web_assets=web/'assets';web_assets.mkdir(parents=True,exist_ok=True)
    if not blender_ok:
        shutil.copy2(root/'assets'/'card.glb',web_assets/'card.glb')
    cfg=json.loads(config.read_text(encoding='utf-8-sig'));cfg['assets']={name:'./assets/'+name+'.png' for name in ['subject','background','text','lineart']};cfg['assets']['model']='./assets/card.glb'
    (web/'card-config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    for name in ['subject.png','background.png','text.png','lineart.png']:shutil.copy2(root/'assets'/name,web/'assets'/name)
    if not a.skip_npm:
        npm=shutil.which('npm.cmd') or shutil.which('npm')
        if not npm:raise RuntimeError('Install Node.js/npm, then run npm install --ignore-scripts in web/')
        subprocess.run([npm,'install','--ignore-scripts','--no-audit','--no-fund'],cwd=web,check=True)
    if blender_ok:print('Completed:',root/'card.blend')
    else:print('Completed with fallback GLB (no card.blend)')
    print('Preview: node',web/'server.mjs');print('Open http://127.0.0.1:4173 after starting the server')
if __name__=='__main__':main()
