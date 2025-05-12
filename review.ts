// https://github.com/tweaselORG/parse-tunes

import { fetchTopApps, charts, countries, genres } from 'parse-tunes';

(async () => {
    const topChart = await fetchTopApps({ genre: genres.all, chart: charts.topFreeIphone, country: countries.DE });
    console.log(topChart.length); // 200
    console.log(topChart[0]); // 1186271926
})();

import { fetchAppDetails } from 'parse-tunes';

(async () => {
    const appDetails = await fetchAppDetails({
        appId: 284882215,
        platforms: ['iphone'],
        attributes: ['artistName', 'customArtwork'],
        country: 'DE',
        language: 'de-DE',
    });
    console.log(appDetails.artistName);
    // Meta Platforms, Inc.
    console.log(appDetails.platformAttributes.ios?.customAttributes.default.default.customArtwork.url);
    // https://is5-ssl.mzstatic.com/image/thumb/Purple113/v4/45/ab/be/45abbeac-3a7e-aa86-c1c5-007c09df6d7c/Icon-Production-0-1x_U007emarketing-0-7-0-85-220.png/{w}x{h}{c}.{f}
})();

import { fetchAppDetails, fetchMediaApiToken } from 'parse-tunes';

(async () => {
    const token = await fetchMediaApiToken();

    for (const appId of [1444383602, 490109661, 462054704]) {
        const appDetails = await fetchAppDetails({
            appId,
            platforms: ['ipad', 'watch'],
            attributes: ['bundleId', 'isIOSBinaryMacOSCompatible'],
            country: 'US',
            language: 'en-US',
            token,
        });
        console.log(appDetails.platformAttributes.ios?.bundleId, '::', appDetails.isIOSBinaryMacOSCompatible);
    }
})();

import { fetchAppDetails } from 'parse-tunes';

(async () => {
    const apps = await searchApps({ searchTerm: 'education', country: 'DE', language: 'en-GB' });

    for (const app of apps) console.log(app.name);
    // Microsoft OneNote
    // Goodnotes 6
    // StudyCards - Karteikarten
    // …
})();

