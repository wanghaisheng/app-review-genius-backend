// https://github.com/facundoolano/app-store-scraper/blob/bb15f360373f386c87eb63c42b2979be39ea0b0c/lib/constants.js
'use strict';

const collection = {
  TOP_MAC: 'topmacapps',
  TOP_FREE_MAC: 'topfreemacapps',
  TOP_GROSSING_MAC: 'topgrossingmacapps',
  TOP_PAID_MAC: 'toppaidmacapps',
  NEW_IOS: 'newapplications',
  NEW_FREE_IOS: 'newfreeapplications',
  NEW_PAID_IOS: 'newpaidapplications',
  TOP_FREE_IOS: 'topfreeapplications',
  TOP_FREE_IPAD: 'topfreeipadapplications',
  TOP_GROSSING_IOS: 'topgrossingapplications',
  TOP_GROSSING_IPAD: 'topgrossingipadapplications',
  TOP_PAID_IOS: 'toppaidapplications',
  TOP_PAID_IPAD: 'toppaidipadapplications'
};

const category = {
  BOOKS: 6018,
  BUSINESS: 6000,
  CATALOGS: 6022,
  EDUCATION: 6017,
  ENTERTAINMENT: 6016,
  FINANCE: 6015,
  FOOD_AND_DRINK: 6023,
  GAMES: 6014,
  GAMES_ACTION: 7001,
  GAMES_ADVENTURE: 7002,
  GAMES_ARCADE: 7003,
  GAMES_BOARD: 7004,
  GAMES_CARD: 7005,
  GAMES_CASINO: 7006,
  GAMES_DICE: 7007,
  GAMES_EDUCATIONAL: 7008,
  GAMES_FAMILY: 7009,
  GAMES_MUSIC: 7011,
  GAMES_PUZZLE: 7012,
  GAMES_RACING: 7013,
  GAMES_ROLE_PLAYING: 7014,
  GAMES_SIMULATION: 7015,
  GAMES_SPORTS: 7016,
  GAMES_STRATEGY: 7017,
  GAMES_TRIVIA: 7018,
  GAMES_WORD: 7019,
  HEALTH_AND_FITNESS: 6013,
  LIFESTYLE: 6012,
  MAGAZINES_AND_NEWSPAPERS: 6021,
  MAGAZINES_ARTS: 13007,
  MAGAZINES_AUTOMOTIVE: 13006,
  MAGAZINES_WEDDINGS: 13008,
  MAGAZINES_BUSINESS: 13009,
  MAGAZINES_CHILDREN: 13010,
  MAGAZINES_COMPUTER: 13011,
  MAGAZINES_FOOD: 13012,
  MAGAZINES_CRAFTS: 13013,
  MAGAZINES_ELECTRONICS: 13014,
  MAGAZINES_ENTERTAINMENT: 13015,
  MAGAZINES_FASHION: 13002,
  MAGAZINES_HEALTH: 13017,
  MAGAZINES_HISTORY: 13018,
  MAGAZINES_HOME: 13003,
  MAGAZINES_LITERARY: 13019,
  MAGAZINES_MEN: 13020,
  MAGAZINES_MOVIES_AND_MUSIC: 13021,
  MAGAZINES_POLITICS: 13001,
  MAGAZINES_OUTDOORS: 13004,
  MAGAZINES_FAMILY: 13023,
  MAGAZINES_PETS: 13024,
  MAGAZINES_PROFESSIONAL: 13025,
  MAGAZINES_REGIONAL: 13026,
  MAGAZINES_SCIENCE: 13027,
  MAGAZINES_SPORTS: 13005,
  MAGAZINES_TEENS: 13028,
  MAGAZINES_TRAVEL: 13029,
  MAGAZINES_WOMEN: 13030,
  MEDICAL: 6020,
  MUSIC: 6011,
  NAVIGATION: 6010,
  NEWS: 6009,
  PHOTO_AND_VIDEO: 6008,
  PRODUCTIVITY: 6007,
  REFERENCE: 6006,
  SHOPPING: 6024,
  SOCIAL_NETWORKING: 6005,
  SPORTS: 6004,
  TRAVEL: 6003,
  UTILITIES: 6002,
  WEATHER: 6001
};

const device = {
  IPAD: 'iPadSoftware',
  MAC: 'macSoftware',
  ALL: 'software'
};

const sort = {
  RECENT: 'mostRecent',
  HELPFUL: 'mostHelpful'
};

// From https://github.com/gonzoua/random-stuff/blob/master/appstorereviews.rb
const markets = {
  MV: 143488, // Maldives
  BD: 143490, // Bangladesh. Note: no entries for this market
  RS: 143500, // Serbia
  DO: 143508, // Dominican Republic
  KZ: 143517, // Kazakhstan
  CI: 143527, // Cote d'Ivoire
  BS: 143539, // Bahamas
  AG: 143540, // Antigua and Barbuda
  KN: 143548, // Saint Kitts and Nevis
  LC: 143549, // Saint Lucia
  VC: 143550, // Saint Vincent and the Grenadines
  TT: 143551, // Trinidad and Tobago
  TC: 143552, // Turks and Caicos Islands
  LY: 143567, // Libya
  MM: 143570, // Myanmar
  CM: 143574, // Cameroon
  AL: 143575, // Albania
  BJ: 143576, // Benin
  BT: 143577, // Bhutan
  BF: 143578, // Burkina Faso
  KH: 143579, // Cambodia
  CV: 143580, // Cape Verde
  TD: 143581, // Chad
  CG: 143582, // Congo
  FJ: 143583, // Fiji
  GM: 143584, // Gambia
  GW: 143585, // Guinea-Bissau
  KG: 143586, // Kyrgyzstan
  LA: 143587, // Laos
  LR: 143588, // Liberia
  MW: 143589, // Malawi
  MR: 143590, // Mauritania
  FM: 143591, // Micronesia, Federated States of
  MN: 143592, // Mongolia
  MZ: 143593, // Mozambique
  NA: 143594, // Namibia
  PW: 143595, // Palau
  PG: 143597, // Papua New Guinea
  ST: 143598, // Sao Tome and Principe
  SC: 143599, // Seychelles
  SL: 143600, // Sierra Leone
  SB: 143601, // Solomon Islands
  SZ: 143602, // Eswatini
  TJ: 143603, // Tajikistan
  TM: 143604, // Turkmenistan
  ZW: 143605, // Zimbabwe
  NR: 143606, // Nauru
  TO: 143608, // Tonga
  VU: 143609, // Vanuatu
  AF: 143610, // Afghanistan
  BA: 143612, // Bosnia and Herzegovina
  CD: 143613, // Congo, Democratic Republic of the
  GA: 143614, // Gabon
  GE: 143615, // Georgia
  IQ: 143617, // Iraq
  ME: 143619, // Montenegro
  MA: 143620, // Morocco
  RW: 143621, // Rwanda
  ZM: 143622, // Zambia
  XK: 143624, // Kosovo
  DZ: 143563,
  AO: 143564,
  AI: 143538,
  AR: 143505,
  AM: 143524,
  AU: 143460,
  AT: 143445,
  AZ: 143568,
  BH: 143559,
  BB: 143541,
  BY: 143565,
  BE: 143446,
  BZ: 143555,
  BM: 143542,
  BO: 143556,
  BW: 143525,
  BR: 143503,
  VG: 143543,
  BN: 143560,
  BG: 143526,
  CA: 143455,
  KY: 143544,
  CL: 143483,
  CN: 143465,
  CO: 143501,
  CR: 143495,
  HR: 143494,
  CY: 143557,
  CZ: 143489,
  DK: 143458,
  DM: 143545,
  EC: 143509,
  EG: 143516,
  SV: 143506,
  EE: 143518,
  FI: 143447,
  FR: 143442,
  DE: 143443,
  GB: 143444,
  GH: 143573,
  GR: 143448,
  GD: 143546,
  GT: 143504,
  GY: 143553,
  HN: 143510,
  HK: 143463,
  HU: 143482,
  IS: 143558,
  IN: 143467,
  ID: 143476,
  IE: 143449,
  IL: 143491,
  IT: 143450,
  JM: 143511,
  JP: 143462,
  JO: 143528,
  KE: 143529,
  KR: 143466,
  KW: 143493,
  LV: 143519,
  LB: 143497,
  LT: 143520,
  LU: 143451,
  MO: 143515,
  MK: 143530,
  MG: 143531,
  MY: 143473,
  ML: 143532,
  MT: 143521,
  MU: 143533,
  MX: 143468,
  MS: 143547,
  NP: 143484,
  NL: 143452,
  NZ: 143461,
  NI: 143512,
  NE: 143534,
  NG: 143561,
  NO: 143457,
  OM: 143562,
  PK: 143477,
  PA: 143485,
  PY: 143513,
  PE: 143507,
  PH: 143474,
  PL: 143478,
  PT: 143453,
  QA: 143498,
  RO: 143487,
  RU: 143469,
  SA: 143479,
  SN: 143535,
  SG: 143464,
  SK: 143496,
  SI: 143499,
  ZA: 143472,
  ES: 143454,
  LK: 143486,
  SR: 143554,
  SE: 143456,
  CH: 143459,
  TW: 143470,
  TZ: 143572,
  TH: 143475,
  TN: 143536,
  TR: 143480,
  UG: 143537,
  UA: 143492,
  AE: 143481,
  US: 143441,
  UY: 143514,
  UZ: 143566,
  VE: 143502,
  VN: 143471,
  YE: 143571
};

module.exports = {collection, category, device, sort, markets};
