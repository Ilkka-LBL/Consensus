from Consensus.AsyncOGP import OpenGeographyLookup

import asyncio

# Run this like:

def main():
    ogl = OpenGeographyLookup(max_retries=30)
    asyncio.run(ogl.initialize())
    asyncio.run(ogl.build_lookup(replace_old=True))

if __name__ == "__main__":
    main()

# or inside Jupyter notebooks:
"""
# %%
async def main():
    ogl = OpenGeographyLookup(max_retries=30)
    await ogl.initialize()
    await ogl.build_lookup(replace_old=True)
# in a new cell:
await main()
"""