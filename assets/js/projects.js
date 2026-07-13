/**
 * PlanetArt QA 项目配置
 * 按业务线分组，便于 QA 按项目维度管理测试资源
 */
const PROJECT_GROUPS = [
  {
    id: 'planetart',
    name: 'PlanetArt 内部',
    icon: '🏢',
    description: '内部管理、IPS 生产、直邮系统',
  },
  {
    id: 'cafepress',
    name: 'CafePress',
    icon: '☕',
    description: 'CafePress 多区域站点',
  },
  {
    id: 'cards',
    name: '卡片 & 印刷',
    icon: '🎴',
    description: '贺卡、照片印刷、Canvas 业务',
  },
  {
    id: 'customcase',
    name: '手机壳',
    icon: '📱',
    description: 'MyCustomCase 系列站点',
  },
  {
    id: 'gifts',
    name: '礼品 & 生活',
    icon: '🎁',
    description: '礼品、个性化定制、装饰品类',
  },

];

const PROJECTS = [
  { id: 0,   short_name: 'ADMIN',  domain: 'admin.planetart.com',           group: 'planetart',   icon: '⚙️',  env: 'prod' },
  { id: 99,  short_name: 'IPS',    domain: 'ips.planetart.com',             group: 'planetart',   icon: '🖨️',  env: 'prod' },
  { id: 150, short_name: 'ISM',    domain: 'dm.planetart.com',              group: 'planetart',   icon: '✉️',  env: 'prod' },

  { id: 169, short_name: 'CPBUS',  domain: 'www.cafepress.com/business',             group: 'cafepress',   icon: '🇺🇸',  env: 'prod' },
  { id: 170, short_name: 'CAFUS',  domain: 'www.cafepress.com',     group: 'cafepress',   icon: '🔬',  env: 'Prod' },
  { id: 171, short_name: 'CAFAU',  domain: 'www.cafepress.com.au',          group: 'cafepress',   icon: '🇦🇺',  env: 'prod' },
  { id: 172, short_name: 'CAFUK',  domain: 'www.cafepress.co.uk',           group: 'cafepress',   icon: '🇬🇧',  env: 'prod' },
  { id: 173, short_name: 'CAFCA',  domain: 'www.cafepress.ca',              group: 'cafepress',   icon: '🇨🇦',  env: 'prod' },
  
  { id: 1,   short_name: 'STI',    domain: 'www.simplytoimpress.com',       group: 'cards',       icon: '💌',  env: 'prod' },
  { id: 2,   short_name: 'PA',     domain: 'www.photoaffections.com',       group: 'cards',       icon: '📷',  env: 'prod' },
  { id: 3,   short_name: 'CW',     domain: 'www.canvasworld.com',           group: 'cards',       icon: '🖼️',  env: 'prod' },
  { id: 4,   short_name: 'STIUK',  domain: 'www.simplytoimpress.co.uk',     group: 'cards',       icon: '🇬🇧',  env: 'prod' },

  { id: 6,   short_name: 'MCC',    domain: 'www.mycustomcase.com',          group: 'customcase',  icon: '📱',  env: 'prod' },
  { id: 8,   short_name: 'MCCUK',  domain: 'www.mycustomcase.co.uk',        group: 'customcase',  icon: '🇬🇧',  env: 'prod' },
  { id: 13,  short_name: 'MCCBB',  domain: 'bestbuy.mycustomcase.com',      group: 'customcase',  icon: '🛒',  env: 'prod' },

  { id: 160, short_name: 'LLANE',  domain: 'www.legacylane.com',            group: 'gifts',       icon: '🛤️',  env: 'prod' },
  { id: 161, short_name: 'GIFTS',  domain: 'www.gifts.com',                 group: 'gifts',       icon: '🎁',  env: 'prod' },
  { id: 162, short_name: 'PKPIP',  domain: 'www.parkerandpip.com',          group: 'gifts',       icon: '🐾',  env: 'prod' },
  { id: 163, short_name: 'PCRUS',  domain: 'www.personalcreations.com',     group: 'gifts',       icon: '🇺🇸',  env: 'prod' },
  { id: 164, short_name: 'PCRUK',  domain: 'www.personalcreations.com',     group: 'gifts',       icon: '🇬🇧',  env: 'prod' },
  { id: 165, short_name: 'STKUS',  domain: 'www.stockingshop.com',          group: 'gifts',       icon: '🧦',  env: 'prod' },
  { id: 166, short_name: 'STKUK',  domain: 'www.stockingshop.com',          group: 'gifts',       icon: '🇬🇧',  env: 'prod' },
  { id: 167, short_name: 'ORNUS',  domain: 'www.ornamentstreet.com',        group: 'gifts',       icon: '🎄',  env: 'prod' },
  { id: 168, short_name: 'BAUUK',  domain: 'www.baubles.co.uk',             group: 'gifts',       icon: '💎',  env: 'prod' },

  
];

function getProjectById(id) {
  return PROJECTS.find(p => p.id === Number(id));
}

function getProjectUrl(project, protocol = 'https') {
  return `${protocol}://${project.domain}`;
}

function getProjectsByGroup(groupId) {
  return PROJECTS.filter(p => p.group === groupId);
}

function getGroupById(groupId) {
  return PROJECT_GROUPS.find(g => g.id === groupId);
}
