import {build} from 'esbuild';
await build({entryPoints:['src/app.tsx'],bundle:true,outfile:'../backend/static/app.js',minify:true,jsx:'automatic'});
