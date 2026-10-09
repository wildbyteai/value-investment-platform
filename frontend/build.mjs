import {build} from 'esbuild';
await build({entryPoints:['src/main.tsx'],bundle:true,outfile:'../backend/static/app.js',minify:true,jsx:'automatic',charset:'utf8',legalComments:'eof'});
