evalscript_true_color = """
//VERSION=3

function setup() {
    return {
        input: [{
            bands: ["B02", "B03", "B04"]
        }],
        output: {
            bands: 3
            sampleType: "UINT8"
        }
    };
}

function evaluatePixel(sample) {
    return [sample.B04, sample.B03, sample.B02];
}
"""

#NDVI (Normalized Difference Vegetation Index)
evalscript_nvdi = """
//VERSION=3
function setup() {
    return {
        input: ["B08", "B04"],
        output: { 
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}
function evaluatePixel(sample) {
  return [(sample.B08 - sample.B04) / (sample.B08 + sample.B04)];
}
"""

#EVI (Enhanced Vegetation Index)
evalscript_evi="""
//VERSION=3
function setup() {
    return {
        input: ["B02", "B04", "B08"],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(samples) {
    return [2.5 * (samples.B08 - samples.B04) / ((samples.B08 + 6.0 * samples.B04 - 7.5 * samples.B02) + 1.0)];
}
"""

#GNDVI (Green Normalized Difference Vegetation Index)
evalscript_gndvi="""
//VERSION=3
function setup() {
    return {
        input: ["B08", "B03"],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}
function evaluatePixel(sample) {
  return [(sample.B08 - sample.B03) / (sample.B08 + sample.B03)];
}
"""

#NDRE (Normalized Difference Red Edge Index)
evalscript_ndre="""
//VERSION=3
function setup() {
    return {
        input: ["B08", "B05"],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}
function evaluatePixel(sample) {
  return [(sample.B08 - sample.B05) / (sample.B08 + sample.B05)];
}
"""

#SAVI (Soil Adjusted Vegetation Index, with L = 0.5)
evalscript_savi="""
//VERSION=3
function setup() {
    return {
        input: ["B08", "B04"],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}
function evaluatePixel(sample) {
  let L = 0.5;
  return [((sample.B08 - sample.B04) / (sample.B08 + sample.B04 + L)) * (1.0 + L)];
}
"""

#ARVI (Atmospherically Resistant Vegetation Index)
evalscript_arvi="""
//VERSION=3
function setup() {
    return {
        input: ["B02", "B04", "B08"],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}
function evaluatePixel(sample) {
  let redCorr = 2.0 * sample.B04 - sample.B02;
  return [(sample.B08 - redCorr) / (sample.B08 + redCorr)];
}
"""
evalscript_true_color_optimized="""
//VERSION=3

function setup() {
return {
    input: ["B04", "B03", "B02", "dataMask"],
    output: { bands: 4 }
};
}

// Contrast enhance / highlight compress


const maxR = 3.0; // max reflectance

const midR = 0.13;
const sat = 1.2;
const gamma = 1.8;

function evaluatePixel(smp) {
const rgbLin = satEnh(sAdj(smp.B04), sAdj(smp.B03), sAdj(smp.B02));
return [sRGB(rgbLin[0]), sRGB(rgbLin[1]), sRGB(rgbLin[2]), smp.dataMask];
}

function sAdj(a) {
return adjGamma(adj(a, midR, 1, maxR));
}

const gOff = 0.01;
const gOffPow = Math.pow(gOff, gamma);
const gOffRange = Math.pow(1 + gOff, gamma) - gOffPow;

function adjGamma(b) {
return (Math.pow((b + gOff), gamma) - gOffPow) / gOffRange;
}

// Saturation enhancement

function satEnh(r, g, b) {
const avgS = (r + g + b) / 3.0 * (1 - sat);
return [clip(avgS + r * sat), clip(avgS + g * sat), clip(avgS + b * sat)];
}

function clip(s) {
return s < 0 ? 0 : s > 1 ? 1 : s;
}

//contrast enhancement with highlight compression

function adj(a, tx, ty, maxC) {
var ar = clip(a / maxC, 0, 1);
return ar * (ar * (tx / maxC + ty - 1) - ty) / (ar * (2 * tx / maxC - 1) - tx / maxC);
}

const sRGB = (c) => c <= 0.0031308 ? (12.92 * c) : (1.055 * Math.pow(c, 0.41666666666) - 0.055); 
"""

INDEX_DICT = {
    'nvdi':evalscript_nvdi,
    'evi':evalscript_evi,
    'gndvi':evalscript_gndvi,
    'ndre':evalscript_ndre,
    'savi':evalscript_savi,
    'arvi':evalscript_arvi,
    'rgb':evalscript_true_color,
    'rgb_optimized':evalscript_true_color_optimized
    }   