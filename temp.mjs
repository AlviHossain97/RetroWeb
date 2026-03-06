import { Nostalgist } from 'nostalgist';

async function main() {
    const coreUrl = await Nostalgist.core('fceumm');
    console.log(coreUrl);
}

main().catch(console.error);
