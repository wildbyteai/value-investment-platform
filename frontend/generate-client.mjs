import fs from 'node:fs';
import openapiTS,{astToString} from 'openapi-typescript';
const doc=JSON.parse(fs.readFileSync('../contracts/openapi-v0001.json','utf8'));
fs.writeFileSync('src/api-schema.ts',astToString(await openapiTS(doc)));
