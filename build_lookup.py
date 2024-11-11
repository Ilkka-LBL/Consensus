from Consensus import OpenGeography, TFL
import asyncio


# Run this like:
async def main():
    retries = 100
    tfl = TFL(max_retries=retries)
    await tfl.initialise()
    await tfl.build_lookup(replace_old=True)

    ogl = OpenGeography(max_retries=retries)
    await ogl.initialise()
    await ogl.build_lookup(replace_old=True)

if __name__ == "__main__":
    asyncio.run(main())

# or inside Jupyter notebooks:
"""
# %%
async def main():
    ogl = OpenGeography(max_retries=30)
    await ogl.initialise()
    await ogl.build_lookup(replace_old=True)
# in a new cell:
await main()
"""
