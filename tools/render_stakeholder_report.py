"""Render with the bundled DOCX renderer and task-local CJK font configuration."""
from pathlib import Path
import os, subprocess, shutil

root=Path(__file__).resolve().parents[1]
python='/Users/kyle/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
renderer='/Users/kyle/.codex/plugins/cache/openai-primary-runtime/documents/26.905.11957/skills/documents/render_docx.py'
render_dir=root/'tmp/stakeholder-report/render-v0.6'
docx=root/'output/documents/value-investment-system-report-v0.6.docx'
env=os.environ.copy()
env['FONTCONFIG_FILE']=str(root/'tmp/stakeholder-report/fonts.conf')
env['SAL_FONTPATH']='/System/Library/Fonts'
subprocess.run([python,renderer,str(docx),'--output_dir',str(render_dir),'--emit_pdf','--dpi','120'],env=env,check=True)
target=root/'output/pdf/value-investment-system-report-v0.6.pdf'
target.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(render_dir/(docx.stem+'.pdf'),target)
print('PDF_RENDERED',target)
print('VISUAL_REVIEW_REQUIRED',render_dir)
