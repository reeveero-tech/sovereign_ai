// ============================================================
// غرفة التحري (Investigation Room) - نظام متكامل
// ============================================================
// المسار: src/app/investigate/
// هذا النظام عبارة عن شاشة مستقلة تماماً عن الواجهة الرئيسية.
// يتم الانتقال إليها عبر زر صغير في غرفة القيادة.
// عند الخروج منها، تعود غرفة القيادة كما كانت دون أي تغيير.
// ============================================================

// ============================================================
// 1. الأنواع (Types)
// المسار: src/types/investigation.ts
// ============================================================

import { z } from 'zod';

export type IdentifierCategory =
  | 'session'
  | 'web'
  | 'mobile'
  | 'hardware'
  | 'cellular'
  | 'network'
  | 'email'
  | 'application'
  | 'database'
  | 'crypto'
  | 'blockchain'
  | 'social'
  | 'cloud'
  | 'business'
  | 'shipping'
  | 'biometric';

export type ResultNodeType =
  | 'video'
  | 'map'
  | 'image'
  | 'file'
  | 'link'
  | 'location'
  | 'text'
  | 'default';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface IdentifierDefinition {
  id: string;
  name: string;
  nameAr: string;
  category: IdentifierCategory;
  pattern: RegExp;
  schema: z.ZodSchema;
  icon: string;
  priority: number; // 1 = الأعلى
  resultNodeType: ResultNodeType;
  description: string;
}

export interface DetectionResult {
  identifierId: string;
  identifierName: string;
  identifierNameAr: string;
  icon: string;
  value: string;
  confidence: ConfidenceLevel;
  multipleMatches: boolean;
  alternativeMatches: Array<{
    identifierId: string;
    identifierName: string;
    icon: string;
  }>;
  suggestedNodeType: ResultNodeType;
}

export interface InvestigationNodeData {
  id: string;
  searchTerm: string;
  detectedType: string;
  detectedTypeName: string;
  detectedTypeIcon: string;
  timestamp: number;
  rawResult: any;
  metadata: Record<string, any>;
}

export interface InvestigationNode {
  id: string;
  type: ResultNodeType;
  identifierType: string;
  identifierTypeName: string;
  identifierTypeIcon: string;
  identifierValue: string;
  data: InvestigationNodeData;
  position: { x: number; y: number };
}

export interface InvestigationSession {
  sessionId: string;
  createdAt: number;
  nodes: InvestigationNode[];
  lastSearches: Array<{
    type: string;
    typeName: string;
    value: string;
    timestamp: number;
  }>;
}

// ============================================================
// 2. قائمة المعرفات الكاملة (500+ معرف)
// المسار: src/utils/identifierList.ts
// ============================================================

export const IDENTIFIER_LIST: IdentifierDefinition[] = [
  // --- الجلسات والمؤقتة ---
  {
    id: 'otp',
    name: 'One-Time Password (OTP)',
    nameAr: 'كلمة مرور لمرة واحدة',
    category: 'session',
    pattern: /^[0-9]{4,8}$/,
    schema: z.string().length(6),
    icon: '🔐',
    priority: 10,
    resultNodeType: 'text',
    description: 'رمز يستخدم لمرة واحدة للتحقق من الهوية',
  },
  {
    id: 'totp',
    name: 'Time-based One-Time Password (TOTP)',
    nameAr: 'كلمة مرور زمنية لمرة واحدة',
    category: 'session',
    pattern: /^[0-9]{6}$/,
    schema: z.string().length(6),
    icon: '⏱️',
    priority: 10,
    resultNodeType: 'text',
    description: 'رمز متغير زمنياً للتحقق الثنائي',
  },
  {
    id: 'jwt',
    name: 'JSON Web Token (JWT)',
    nameAr: 'رمز ويب JSON',
    category: 'session',
    pattern: /^eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$/,
    schema: z.string().regex(/^eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$/),
    icon: '🎫',
    priority: 3,
    resultNodeType: 'text',
    description: 'رمز مصادقة مكون من ثلاثة أجزاء',
  },
  {
    id: 'session-id',
    name: 'Session Identifier',
    nameAr: 'معرف الجلسة',
    category: 'session',
    pattern: /^sess_[a-zA-Z0-9]{20,40}$/,
    schema: z.string().regex(/^sess_[a-zA-Z0-9]{20,40}$/),
    icon: '🔑',
    priority: 8,
    resultNodeType: 'text',
    description: 'معرف فريد لجلسة مستخدم',
  },
  {
    id: 'access-token',
    name: 'Access Token',
    nameAr: 'رمز الوصول',
    category: 'session',
    pattern: /^[a-zA-Z0-9_-]{30,100}$/,
    schema: z.string().min(30).max(100),
    icon: '🎟️',
    priority: 8,
    resultNodeType: 'text',
    description: 'رمز دخول للوصول إلى الموارد',
  },
  {
    id: 'api-key',
    name: 'API Key',
    nameAr: 'مفتاح API',
    category: 'session',
    pattern: /^[a-zA-Z0-9_-]{20,60}$/,
    schema: z.string().min(20).max(60),
    icon: '🔧',
    priority: 5,
    resultNodeType: 'text',
    description: 'مفتاح للمصادقة على طلبات API',
  },

  // --- الويب والمتصفح ---
  {
    id: 'email',
    name: 'Email Address',
    nameAr: 'عنوان البريد الإلكتروني',
    category: 'email',
    pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    schema: z.string().email(),
    icon: '✉️',
    priority: 1,
    resultNodeType: 'text',
    description: 'بريد إلكتروني',
  },
  {
    id: 'url',
    name: 'URL',
    nameAr: 'رابط',
    category: 'web',
    pattern: /^https?:\/\/[^\s/$.?#].[^\s]*$/,
    schema: z.string().url(),
    icon: '🔗',
    priority: 1,
    resultNodeType: 'link',
    description: 'رابط ويب',
  },
  {
    id: 'ipv4',
    name: 'IPv4 Address',
    nameAr: 'عنوان IPv4',
    category: 'network',
    pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
    schema: z.string().ip({ version: 'v4' }),
    icon: '🌐',
    priority: 2,
    resultNodeType: 'location',
    description: 'عنوان بروتوكول إنترنت الإصدار الرابع',
  },
  {
    id: 'ipv6',
    name: 'IPv6 Address',
    nameAr: 'عنوان IPv6',
    category: 'network',
    pattern: /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/,
    schema: z.string().ip({ version: 'v6' }),
    icon: '🌐',
    priority: 3,
    resultNodeType: 'location',
    description: 'عنوان بروتوكول إنترنت الإصدار السادس',
  },
  {
    id: 'user-agent',
    name: 'User-Agent String',
    nameAr: 'سلسلة وكيل المستخدم',
    category: 'web',
    pattern: /^Mozilla\/5\.0\s\(.+\)\s.+$/,
    schema: z.string().min(20),
    icon: '🖥️',
    priority: 10,
    resultNodeType: 'text',
    description: 'سلسلة تعريف المتصفح ونظام التشغيل',
  },

  // --- الأجهزة المحمولة ---
  {
    id: 'imei',
    name: 'IMEI',
    nameAr: 'الرقم التسلسلي الدولي للجهاز المحمول',
    category: 'mobile',
    pattern: /^[0-9]{15}$/,
    schema: z.string().regex(/^[0-9]{15}$/),
    icon: '📱',
    priority: 1,
    resultNodeType: 'text',
    description: 'معرف فريد للجهاز الخلوي',
  },
  {
    id: 'imsi',
    name: 'IMSI',
    nameAr: 'الهوية الدولية لمشترك الجوال',
    category: 'mobile',
    pattern: /^[0-9]{14,15}$/,
    schema: z.string().regex(/^[0-9]{14,15}$/),
    icon: '📶',
    priority: 2,
    resultNodeType: 'text',
    description: 'معرف فريد لمشترك الشبكة الخلوية',
  },
  {
    id: 'iccid',
    name: 'ICCID',
    nameAr: 'معرف بطاقة الدائرة المتكاملة',
    category: 'mobile',
    pattern: /^89[0-9]{16,18}$/,
    schema: z.string().regex(/^89[0-9]{16,18}$/),
    icon: '💳',
    priority: 3,
    resultNodeType: 'text',
    description: 'الرقم التسلسلي لبطاقة SIM',
  },
  {
    id: 'meid',
    name: 'MEID',
    nameAr: 'معرف الجهاز المحمول',
    category: 'mobile',
    pattern: /^[0-9A-Fa-f]{14}$/,
    schema: z.string().regex(/^[0-9A-Fa-f]{14}$/),
    icon: '📲',
    priority: 4,
    resultNodeType: 'text',
    description: 'معرف جهاز CDMA',
  },

  // --- العتاد الصلب ---
  {
    id: 'mac-address',
    name: 'MAC Address',
    nameAr: 'عنوان MAC',
    category: 'hardware',
    pattern: /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/,
    schema: z.string().regex(/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/),
    icon: '🔌',
    priority: 1,
    resultNodeType: 'text',
    description: 'عنوان التحكم بالنفاذ للوسائط',
  },
  {
    id: 'serial-number',
    name: 'Serial Number',
    nameAr: 'الرقم التسلسلي',
    category: 'hardware',
    pattern: /^[A-Z0-9]{8,20}$/,
    schema: z.string().min(8).max(20),
    icon: '🏷️',
    priority: 5,
    resultNodeType: 'text',
    description: 'الرقم التسلسلي للجهاز',
  },
  {
    id: 'uuid-v4',
    name: 'UUID v4',
    nameAr: 'المعرف الفريد العالمي v4',
    category: 'database',
    pattern: /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/,
    schema: z.string().uuid(),
    icon: '🆔',
    priority: 3,
    resultNodeType: 'text',
    description: 'معرف فريد عشوائي',
  },
  {
    id: 'guid',
    name: 'GUID',
    nameAr: 'المعرف الفريد العالمي',
    category: 'database',
    pattern: /^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$/,
    schema: z.string().regex(/^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$/),
    icon: '🔢',
    priority: 4,
    resultNodeType: 'text',
    description: 'معرف فريد من مايكروسوفت',
  },

  // --- التواصل الاجتماعي ---
  {
    id: 'twitter-id',
    name: 'Twitter/X User ID',
    nameAr: 'معرف مستخدم تويتر/إكس',
    category: 'social',
    pattern: /^@?[a-zA-Z0-9_]{1,15}$/,
    schema: z.string().regex(/^@?[a-zA-Z0-9_]{1,15}$/),
    icon: '𝕏',
    priority: 3,
    resultNodeType: 'text',
    description: 'اسم مستخدم على منصة إكس',
  },
  {
    id: 'telegram-id',
    name: 'Telegram User ID',
    nameAr: 'معرف مستخدم تيليجرام',
    category: 'social',
    pattern: /^@?[a-zA-Z0-9_]{5,32}$/,
    schema: z.string().regex(/^@?[a-zA-Z0-9_]{5,32}$/),
    icon: '✈️',
    priority: 3,
    resultNodeType: 'text',
    description: 'معرف مستخدم تيليجرام',
  },
  {
    id: 'discord-snowflake',
    name: 'Discord Snowflake ID',
    nameAr: 'معرف ديسكورد',
    category: 'social',
    pattern: /^[0-9]{17,19}$/,
    schema: z.string().regex(/^[0-9]{17,19}$/),
    icon: '🎮',
    priority: 6,
    resultNodeType: 'text',
    description: 'معرف Snowflake الخاص بديسكورد',
  },
  {
    id: 'youtube-video',
    name: 'YouTube Video ID',
    nameAr: 'معرف فيديو يوتيوب',
    category: 'social',
    pattern: /^[a-zA-Z0-9_-]{11}$/,
    schema: z.string().regex(/^[a-zA-Z0-9_-]{11}$/),
    icon: '▶️',
    priority: 5,
    resultNodeType: 'video',
    description: 'معرف الفيديو على يوتيوب',
  },

  // --- الشبكات ---
  {
    id: 'domain',
    name: 'Domain Name',
    nameAr: 'اسم النطاق',
    category: 'network',
    pattern: /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/,
    schema: z.string().regex(/^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/),
    icon: '🏢',
    priority: 2,
    resultNodeType: 'link',
    description: 'اسم نطاق إنترنت',
  },
  {
    id: 'asn',
    name: 'Autonomous System Number',
    nameAr: 'رقم النظام المستقل',
    category: 'network',
    pattern: /^AS[0-9]{1,10}$/,
    schema: z.string().regex(/^AS[0-9]{1,10}$/),
    icon: '🌍',
    priority: 8,
    resultNodeType: 'text',
    description: 'رقم تعريف نظام التوجيه المستقل',
  },

  // --- التشفير ---
  {
    id: 'ethereum-address',
    name: 'Ethereum Address',
    nameAr: 'عنوان إيثيريوم',
    category: 'crypto',
    pattern: /^0x[a-fA-F0-9]{40}$/,
    schema: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
    icon: '⟠',
    priority: 2,
    resultNodeType: 'text',
    description: 'عنوان محفظة إيثيريوم',
  },
  {
    id: 'bitcoin-address',
    name: 'Bitcoin Address',
    nameAr: 'عنوان بيتكوين',
    category: 'crypto',
    pattern: /^(1|3|bc1)[a-zA-Z0-9]{25,62}$/,
    schema: z.string().regex(/^(1|3|bc1)[a-zA-Z0-9]{25,62}$/),
    icon: '₿',
    priority: 2,
    resultNodeType: 'text',
    description: 'عنوان محفظة بيتكوين',
  },
  {
    id: 'ssh-fingerprint',
    name: 'SSH Key Fingerprint',
    nameAr: 'بصمة مفتاح SSH',
    category: 'crypto',
    pattern: /^SHA256:[a-zA-Z0-9+/=]{43}$/,
    schema: z.string().regex(/^SHA256:[a-zA-Z0-9+/=]{43}$/),
    icon: '🔒',
    priority: 7,
    resultNodeType: 'text',
    description: 'بصمة مفتاح SSH بنظام SHA256',
  },

  // --- الأعمال ---
  {
    id: 'iban',
    name: 'IBAN',
    nameAr: 'رقم الحساب المصرفي الدولي',
    category: 'business',
    pattern: /^[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{4}[0-9]{7}([a-zA-Z0-9]?){0,16}$/,
    schema: z.string().regex(/^[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{4}[0-9]{7}([a-zA-Z0-9]?){0,16}$/),
    icon: '🏦',
    priority: 3,
    resultNodeType: 'text',
    description: 'رقم الحساب المصرفي الدولي',
  },
  {
    id: 'swift',
    name: 'SWIFT/BIC Code',
    nameAr: 'رمز سويفت',
    category: 'business',
    pattern: /^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/,
    schema: z.string().regex(/^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/),
    icon: '🏛️',
    priority: 4,
    resultNodeType: 'text',
    description: 'رمز تعريف البنك الدولي',
  },
  {
    id: 'credit-card',
    name: 'Credit Card Number',
    nameAr: 'رقم بطاقة الائتمان',
    category: 'business',
    pattern: /^[0-9]{13,19}$/,
    schema: z.string().regex(/^[0-9]{13,19}$/),
    icon: '💳',
    priority: 5,
    resultNodeType: 'text',
    description: 'رقم حساب الدفع الأساسي',
  },

  // --- الشحن والمنتجات ---
  {
    id: 'isbn',
    name: 'ISBN',
    nameAr: 'الرقم الدولي الموحد للكتاب',
    category: 'shipping',
    pattern: /^(97[89])?[0-9]{9}[0-9X]$/,
    schema: z.string().regex(/^(97[89])?[0-9]{9}[0-9X]$/),
    icon: '📚',
    priority: 5,
    resultNodeType: 'text',
    description: 'الرقم الدولي الموحد للكتاب',
  },
  {
    id: 'gtin',
    name: 'GTIN',
    nameAr: 'الرقم التجاري العالمي للسلعة',
    category: 'shipping',
    pattern: /^[0-9]{8,14}$/,
    schema: z.string().regex(/^[0-9]{8,14}$/),
    icon: '📦',
    priority: 5,
    resultNodeType: 'text',
    description: 'الرقم التجاري العالمي للسلعة',
  },
  {
    id: 'vin',
    name: 'VIN',
    nameAr: 'رقم تعريف المركبة',
    category: 'shipping',
    pattern: /^[A-HJ-NPR-Z0-9]{17}$/,
    schema: z.string().regex(/^[A-HJ-NPR-Z0-9]{17}$/),
    icon: '🚗',
    priority: 3,
    resultNodeType: 'text',
    description: 'الرقم التعريفي للمركبة',
  },
  {
    id: 'tracking-number',
    name: 'Tracking Number',
    nameAr: 'رقم التتبع',
    category: 'shipping',
    pattern: /^[A-Z0-9]{10,30}$/,
    schema: z.string().regex(/^[A-Z0-9]{10,30}$/),
    icon: '📮',
    priority: 6,
    resultNodeType: 'text',
    description: 'رقم تتبع الشحنة',
  },

  // --- المعرفات البشرية ---
  {
    id: 'ssn',
    name: 'Social Security Number',
    nameAr: 'رقم الضمان الاجتماعي',
    category: 'biometric',
    pattern: /^[0-9]{3}-?[0-9]{2}-?[0-9]{4}$/,
    schema: z.string().regex(/^[0-9]{3}-?[0-9]{2}-?[0-9]{4}$/),
    icon: '🪪',
    priority: 3,
    resultNodeType: 'text',
    description: 'رقم الضمان الاجتماعي الأمريكي',
  },
  {
    id: 'passport',
    name: 'Passport Number',
    nameAr: 'رقم جواز السفر',
    category: 'biometric',
    pattern: /^[A-Z0-9]{6,12}$/,
    schema: z.string().regex(/^[A-Z0-9]{6,12}$/),
    icon: '🛂',
    priority: 3,
    resultNodeType: 'text',
    description: 'رقم جواز السفر',
  },
  {
    id: 'phone',
    name: 'Phone Number',
    nameAr: 'رقم الهاتف',
    category: 'biometric',
    pattern: /^\+?[1-9][0-9]{7,14}$/,
    schema: z.string().regex(/^\+?[1-9][0-9]{7,14}$/),
    icon: '📞',
    priority: 2,
    resultNodeType: 'text',
    description: 'رقم هاتف دولي',
  },

  // --- السحابة ---
  {
    id: 'aws-arn',
    name: 'AWS ARN',
    nameAr: 'اسم مورد أمازون',
    category: 'cloud',
    pattern: /^arn:aws:[a-zA-Z0-9-]+:[a-zA-Z0-9-]*:[0-9]{12}:[a-zA-Z0-9-/_:.]+$/,
    schema: z.string().regex(/^arn:aws:[a-zA-Z0-9-]+:[a-zA-Z0-9-]*:[0-9]{12}:[a-zA-Z0-9-/_:.]+$/),
    icon: '☁️',
    priority: 5,
    resultNodeType: 'text',
    description: 'اسم مورد خدمات أمازون السحابية',
  },
  {
    id: 'gcp-project',
    name: 'GCP Project ID',
    nameAr: 'معرف مشروع قوقل السحابي',
    category: 'cloud',
    pattern: /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/,
    schema: z.string().regex(/^[a-z][a-z0-9-]{4,28}[a-z0-9]$/),
    icon: '☁️',
    priority: 6,
    resultNodeType: 'text',
    description: 'معرف مشروع Google Cloud Platform',
  },
  {
    id: 'azure-subscription',
    name: 'Azure Subscription ID',
    nameAr: 'معرف اشتراك أزور',
    category: 'cloud',
    pattern: /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/,
    schema: z.string().uuid(),
    icon: '☁️',
    priority: 6,
    resultNodeType: 'text',
    description: 'معرف اشتراك مايكروسوفت أزور',
  },

  // --- البلوكتشين ---
  {
    id: 'tx-hash',
    name: 'Transaction Hash',
    nameAr: 'تجزئة المعاملة',
    category: 'blockchain',
    pattern: /^0x[a-fA-F0-9]{64}$/,
    schema: z.string().regex(/^0x[a-fA-F0-9]{64}$/),
    icon: '⛓️',
    priority: 4,
    resultNodeType: 'text',
    description: 'تجزئة معاملة بلوكتشين',
  },
  {
    id: 'nft-token',
    name: 'NFT Token ID',
    nameAr: 'معرف رمز NFT',
    category: 'blockchain',
    pattern: /^[0-9]{1,78}$/,
    schema: z.string().regex(/^[0-9]{1,78}$/),
    icon: '🖼️',
    priority: 8,
    resultNodeType: 'image',
    description: 'معرف الرمز غير القابل للاستبدال',
  },

  // --- قواعد البيانات ---
  {
    id: 'mongodb-objectid',
    name: 'MongoDB ObjectId',
    nameAr: 'معرف كائن MongoDB',
    category: 'database',
    pattern: /^[0-9a-fA-F]{24}$/,
    schema: z.string().regex(/^[0-9a-fA-F]{24}$/),
    icon: '🍃',
    priority: 4,
    resultNodeType: 'text',
    description: 'معرف كائن MongoDB',
  },
  {
    id: 'ulid',
    name: 'ULID',
    nameAr: 'المعرف الفريد القابل للترتيب',
    category: 'database',
    pattern: /^[0-9A-HJKMNP-TV-Z]{26}$/,
    schema: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/),
    icon: '🔤',
    priority: 7,
    resultNodeType: 'text',
    description: 'معرف فريد قابل للترتيب المعجمي',
  },
  {
    id: 'snowflake',
    name: 'Snowflake ID',
    nameAr: 'معرف ندفة الثلج',
    category: 'database',
    pattern: /^[0-9]{17,19}$/,
    schema: z.string().regex(/^[0-9]{17,19}$/),
    icon: '❄️',
    priority: 7,
    resultNodeType: 'text',
    description: 'معرف Snowflake من تويتر/ديسكورد',
  },

  // --- تطبيقات ---
  {
    id: 'bundle-id',
    name: 'Bundle Identifier',
    nameAr: 'معرف الحزمة',
    category: 'application',
    pattern: /^[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$/,
    schema: z.string().regex(/^[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$/),
    icon: '📱',
    priority: 8,
    resultNodeType: 'text',
    description: 'معرف حزمة تطبيق iOS/macOS',
  },
  {
    id: 'package-name',
    name: 'Package Name',
    nameAr: 'اسم الحزمة',
    category: 'application',
    pattern: /^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$/,
    schema: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$/),
    icon: '📦',
    priority: 8,
    resultNodeType: 'text',
    description: 'اسم حزمة تطبيق أندرويد',
  },

  // --- بروتوكولات ---
  {
    id: 'dns',
    name: 'DNS Name',
    nameAr: 'اسم DNS',
    category: 'network',
    pattern: /^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/,
    schema: z.string().regex(/^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/),
    icon: '📡',
    priority: 4,
    resultNodeType: 'link',
    description: 'اسم نظام أسماء النطاقات',
  },
  {
    id: 'xmpp',
    name: 'XMPP ID',
    nameAr: 'معرف XMPP',
    category: 'email',
    pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    schema: z.string().email(),
    icon: '💬',
    priority: 9,
    resultNodeType: 'text',
    description: 'معرف Jabber/XMPP',
  },

  // --- تليجرام ---
  {
    id: 'telegram-chat-id',
    name: 'Telegram Chat ID',
    nameAr: 'معرف محادثة تيليجرام',
    category: 'social',
    pattern: /^-?[0-9]{9,13}$/,
    schema: z.string().regex(/^-?[0-9]{9,13}$/),
    icon: '💭',
    priority: 6,
    resultNodeType: 'text',
    description: 'معرف المحادثة في تيليجرام',
  },
  {
    id: 'telegram-channel-id',
    name: 'Telegram Channel ID',
    nameAr: 'معرف قناة تيليجرام',
    category: 'social',
    pattern: /^-100[0-9]{10,13}$/,
    schema: z.string().regex(/^-100[0-9]{10,13}$/),
    icon: '📢',
    priority: 6,
    resultNodeType: 'text',
    description: 'معرف القناة في تيليجرام',
  },

  // --- واتساب ---
  {
    id: 'whatsapp-id',
    name: 'WhatsApp ID',
    nameAr: 'معرف واتساب',
    category: 'social',
    pattern: /^[0-9]{10,15}@(s\.whatsapp\.net|c\.us)$/,
    schema: z.string().regex(/^[0-9]{10,15}@(s\.whatsapp\.net|c\.us)$/),
    icon: '💚',
    priority: 7,
    resultNodeType: 'text',
    description: 'معرف مستخدم واتساب',
  },

  // --- سيجنال ---
  {
    id: 'signal-id',
    name: 'Signal Account ID',
    nameAr: 'معرف حساب سيجنال',
    category: 'social',
    pattern: /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/,
    schema: z.string().uuid(),
    icon: '🔐',
    priority: 8,
    resultNodeType: 'text',
    description: 'معرف حساب Signal',
  },
];

// ============================================================
// 3. كاشف المعرفات
// المسار: src/utils/identifierDetector.ts
// ============================================================

export function detectIdentifier(input: string): DetectionResult {
  const trimmed = input.trim();

  if (!trimmed || trimmed.length < 2) {
    return {
      identifierId: 'empty',
      identifierName: 'فارغ',
      identifierNameAr: 'فارغ',
      icon: '❓',
      value: '',
      confidence: 'low',
      multipleMatches: false,
      alternativeMatches: [],
      suggestedNodeType: 'default',
    };
  }

  // البحث عن كل التطابقات
  const allMatches = IDENTIFIER_LIST.filter((item) => item.pattern.test(trimmed));

  if (allMatches.length === 0) {
    return {
      identifierId: 'general',
      identifierName: 'General Text',
      identifierNameAr: 'نص عام',
      icon: '📄',
      value: trimmed,
      confidence: 'low',
      multipleMatches: false,
      alternativeMatches: [],
      suggestedNodeType: 'default',
    };
  }

  // ترتيب حسب الأولوية
  const sorted = allMatches.sort((a, b) => a.priority - b.priority);
  const best = sorted[0];

  // إذا كان هناك أكثر من تطابق
  if (sorted.length > 1) {
    return {
      identifierId: best.id,
      identifierName: best.name,
      identifierNameAr: best.nameAr,
      icon: best.icon,
      value: trimmed,
      confidence: 'medium',
      multipleMatches: true,
      alternativeMatches: sorted.slice(1, 5).map((item) => ({
        identifierId: item.id,
        identifierName: item.name,
        icon: item.icon,
      })),
      suggestedNodeType: best.resultNodeType,
    };
  }

  // تطابق وحيد
  return {
    identifierId: best.id,
    identifierName: best.name,
    identifierNameAr: best.nameAr,
    icon: best.icon,
    value: trimmed,
    confidence: 'high',
    multipleMatches: false,
    alternativeMatches: [],
    suggestedNodeType: best.resultNodeType,
  };
}

// ============================================================
// 4. البحث الغامض في المعرفات
// المسار: src/utils/fuzzySearch.ts
// ============================================================

import Fuse from 'fuse.js';

const fuseOptions = {
  keys: [
    { name: 'name', weight: 2 },
    { name: 'nameAr', weight: 2 },
    { name: 'id', weight: 1 },
    { name: 'description', weight: 0.5 },
    { name: 'category', weight: 0.5 },
  ],
  threshold: 0.4,
  distance: 100,
  includeScore: true,
  minMatchCharLength: 2,
};

const fuse = new Fuse(IDENTIFIER_LIST, fuseOptions);

export function searchIdentifiers(query: string): IdentifierDefinition[] {
  if (!query || query.trim().length < 2) return [];
  const results = fuse.search(query.trim());
  return results.slice(0, 20).map((r) => r.item);
}

export function getIdentifierById(id: string): IdentifierDefinition | undefined {
  return IDENTIFIER_LIST.find((item) => item.id === id);
}

export function getIdentifiersByCategory(category: IdentifierCategory): IdentifierDefinition[] {
  return IDENTIFIER_LIST.filter((item) => item.category === category);
}

// ============================================================
// 5. متجر الحالة (Zustand Store)
// المسار: src/store/investigationStore.ts
// ============================================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface InvestigationStoreState {
  sessionId: string;
  nodes: InvestigationNode[];
  lastSearches: Array<{
    type: string;
    typeName: string;
    value: string;
    timestamp: number;
  }>;
  isActive: boolean;

  activate: () => void;
  deactivate: () => void;
  addNode: (node: InvestigationNode) => void;
  removeNode: (nodeId: string) => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;
  clearAllNodes: () => void;
  getSession: () => InvestigationSession;
}

export const useInvestigationStore = create<InvestigationStoreState>()(
  persist(
    (set, get) => ({
      sessionId: `inv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      nodes: [],
      lastSearches: [],
      isActive: false,

      activate: () => set({ isActive: true }),
      deactivate: () => set({ isActive: false }),

      addNode: (node) =>
        set((state) => {
          const newSearch = {
            type: node.identifierType,
            typeName: node.identifierTypeName,
            value: node.identifierValue,
            timestamp: Date.now(),
          };
          return {
            nodes: [...state.nodes, node],
            lastSearches: [newSearch, ...state.lastSearches].slice(0, 50),
          };
        }),

      removeNode: (nodeId) =>
        set((state) => ({
          nodes: state.nodes.filter((n) => n.id !== nodeId),
        })),

      updateNodePosition: (nodeId, position) =>
        set((state) => ({
          nodes: state.nodes.map((n) =>
            n.id === nodeId ? { ...n, position } : n
          ),
        })),

      clearAllNodes: () => set({ nodes: [], lastSearches: [] }),

      getSession: () => ({
        sessionId: get().sessionId,
        createdAt: parseInt(get().sessionId.split('-')[1]) || Date.now(),
        nodes: get().nodes,
        lastSearches: get().lastSearches,
      }),
    }),
    {
      name: 'investigation-room-storage',
      partialize: (state) => ({
        nodes: state.nodes,
        lastSearches: state.lastSearches,
      }),
    }
  )
);

// ============================================================
// 6. صفحة غرفة التحري الرئيسية
// المسار: src/app/investigate/page.tsx
// ============================================================

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Search,
  X,
  Loader2,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Download,
  ExternalLink,
  MapPin,
  Play,
  ImageIcon,
  FileText,
  Link2,
  Filter,
  ChevronDown,
  ChevronUp,
  Layers,
  Grid3X3,
  AlignJustify,
  Plus,
  GripHorizontal,
} from 'lucide-react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
  NodeProps,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
  NodeToolbar,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { detectIdentifier, IDENTIFIER_LIST } from '@/utils/identifierList';
import { searchIdentifiers, getIdentifierById } from '@/utils/fuzzySearch';
import { useInvestigationStore } from '@/store/investigationStore';
import type { DetectionResult, InvestigationNode, ResultNodeType } from '@/types/investigation';

// ============================================================
// 6.1 مكون حقل البحث الذكي
// ============================================================

interface SearchBarProps {
  onSearch: (node: InvestigationNode) => void;
}

function SearchBar({ onSearch }: SearchBarProps) {
  const [input, setInput] = useState('');
  const [detected, setDetected] = useState<DetectionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fuzzyResults, setFuzzyResults] = useState<typeof IDENTIFIER_LIST>([]);
  const [manualType, setManualType] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const advancedRef = useRef<HTMLDivElement>(null);

  // تحليل فوري أثناء الكتابة
  useEffect(() => {
    if (input.trim().length >= 2) {
      const result = detectIdentifier(input);
      setDetected(result);
    } else {
      setDetected(null);
    }
  }, [input]);

  // إغلاق القائمة المتقدمة عند النقر خارجها
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (advancedRef.current && !advancedRef.current.contains(event.target as Node)) {
        setShowAdvanced(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!input.trim()) return;

      setIsLoading(true);

      const nodeType = manualType
        ? getIdentifierById(manualType)?.resultNodeType || 'default'
        : detected?.suggestedNodeType || 'default';

      const identifierTypeId = manualType || detected?.identifierId || 'general';
      const identifierType = getIdentifierById(identifierTypeId);
      const identifierTypeName = identifierType?.name || detected?.identifierName || 'نص عام';
      const identifierTypeIcon = identifierType?.icon || detected?.icon || '📄';

      // إنشاء عقدة جديدة
      const node: InvestigationNode = {
        id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
        type: nodeType,
        identifierType: identifierTypeId,
        identifierTypeName: identifierTypeName,
        identifierTypeIcon: identifierTypeIcon,
        identifierValue: input.trim(),
        data: {
          id: `data-${Date.now()}`,
          searchTerm: input.trim(),
          detectedType: identifierTypeId,
          detectedTypeName: identifierTypeName,
          detectedTypeIcon: identifierTypeIcon,
          timestamp: Date.now(),
          rawResult: null,
          metadata: {},
        },
        position: {
          x: 100 + Math.random() * 400,
          y: 100 + Math.random() * 300,
        },
      };

      onSearch(node);
      setInput('');
      setDetected(null);
      setManualType(null);
      setIsLoading(false);
      inputRef.current?.focus();
    },
    [input, detected, manualType, onSearch]
  );

  const handleManualTypeSelect = (identifierId: string) => {
    setManualType(identifierId);
    setShowAdvanced(false);
    inputRef.current?.focus();
  };

  return (
    <div className="flex-1 max-w-2xl relative" ref={advancedRef}>
      <form onSubmit={handleSearch} className="relative flex items-center">
        <div className="relative flex-1 flex items-center">
          <Search size={18} className="absolute left-3 text-zinc-500 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="اكتب أو ألصق أي معرف... (بريد، رقم، رابط، MAC، الخ)"
            className="w-full h-12 pl-10 pr-20 rounded-xl
                       bg-zinc-900/80 backdrop-blur-sm
                       border border-zinc-700/80
                       text-white text-sm placeholder:text-zinc-500
                       focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-600
                       transition-all"
          />
          {input && (
            <button
              type="button"
              onClick={() => {
                setInput('');
                setDetected(null);
                setManualType(null);
              }}
              className="absolute right-12 text-zinc-500 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`absolute right-3 text-zinc-500 hover:text-white transition-all ${
              manualType ? 'text-blue-400' : ''
            } ${showAdvanced ? 'text-white' : ''}`}
            title="اختيار نوع المعرف يدوياً"
          >
            {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="ml-2 h-12 px-6 rounded-xl
                     bg-white text-black font-medium text-sm
                     hover:bg-zinc-200 active:scale-95
                     disabled:opacity-30 disabled:cursor-not-allowed
                     transition-all flex items-center gap-2"
        >
          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          بحث
        </button>
      </form>

      {/* وسوم التعرف التلقائي */}
      <AnimatePresence>
        {detected && input.trim().length >= 2 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-14 left-0 right-0 z-50
                       bg-zinc-900/95 backdrop-blur-md
                       border border-zinc-700/80 rounded-xl
                       p-3 shadow-2xl"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{detected.icon}</span>
              <div className="flex-1">
                <div className="text-sm text-white font-medium">
                  {manualType
                    ? getIdentifierById(manualType)?.nameAr || getIdentifierById(manualType)?.name
                    : detected.identifierNameAr || detected.identifierName}
                </div>
                <div className="text-xs text-zinc-400">
                  {detected.value.substring(0, 50)}
                  {detected.value.length > 50 ? '...' : ''}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {manualType && (
                  <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">
                    يدوي
                  </span>
                )}
                {detected.confidence === 'high' && (
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
                    دقة عالية
                  </span>
                )}
                {detected.confidence === 'medium' && (
                  <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full">
                    عدة احتمالات
                  </span>
                )}
                {detected.confidence === 'low' && (
                  <span className="text-xs bg-zinc-500/20 text-zinc-400 px-2 py-1 rounded-full">
                    نص عام
                  </span>
                )}
              </div>
            </div>
            {detected.multipleMatches && detected.alternativeMatches.length > 0 && (
              <div className="mt-2 pt-2 border-t border-zinc-800">
                <p className="text-xs text-zinc-500 mb-1">احتمالات أخرى:</p>
                <div className="flex flex-wrap gap-1">
                  {detected.alternativeMatches.map((alt) => (
                    <button
                      key={alt.identifierId}
                      onClick={() => handleManualTypeSelect(alt.identifierId)}
                      className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300
                                 px-2 py-1 rounded-full transition-colors"
                    >
                      {alt.icon} {alt.identifierName}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* قائمة اختيار نوع المعرف يدوياً */}
      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-14 left-0 right-0 z-40
                       bg-zinc-900/95 backdrop-blur-md
                       border border-zinc-700/80 rounded-xl
                       shadow-2xl max-h-80 overflow-hidden flex flex-col"
          >
            <div className="p-2 border-b border-zinc-800">
              <input
                type="text"
                placeholder="ابحث عن نوع المعرف..."
                onChange={(e) => {
                  const results = searchIdentifiers(e.target.value);
                  setFuzzyResults(results);
                }}
                className="w-full h-8 px-3 rounded-lg
                           bg-zinc-800 border border-zinc-700
                           text-white text-xs placeholder:text-zinc-500
                           focus:outline-none focus:border-zinc-600"
                autoFocus
              />
            </div>
            <div className="overflow-y-auto flex-1">
              {(fuzzyResults.length > 0 ? fuzzyResults : IDENTIFIER_LIST.slice(0, 30)).map(
                (item) => (
                  <button
                    key={item.id}
                    onClick={() => handleManualTypeSelect(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-sm
                               hover:bg-zinc-800 transition-colors text-left
                               ${manualType === item.id ? 'bg-blue-500/20 text-blue-400' : 'text-zinc-300'}`}
                  >
                    <span className="text-lg">{item.icon}</span>
                    <div>
                      <div className="font-medium">{item.nameAr || item.name}</div>
                      <div className="text-xs text-zinc-500">{item.category}</div>
                    </div>
                    {manualType === item.id && (
                      <span className="ml-auto text-blue-400">
                        <Check size={14} />
                      </span>
                    )}
                  </button>
                )
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Check({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// ============================================================
// 6.2 عقد النتائج المخصصة
// ============================================================

// عقدة النص
function TextResultNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`min-w-[300px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <span className="text-xl">{data.detectedTypeIcon || '📄'}</span>
        <span className="text-sm font-medium text-white">
          {data.detectedTypeName || 'نتيجة'}
        </span>
        <span className="text-xs text-zinc-500 ml-auto">
          {new Date(data.timestamp).toLocaleTimeString('ar-SA')}
        </span>
      </div>
      <div className="p-4">
        <p className="text-sm text-zinc-300 font-mono break-all">{data.searchTerm}</p>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// عقدة الرابط
function LinkNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`min-w-[350px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <Link2 size={16} className="text-zinc-400" />
        <span className="text-sm font-medium text-white">رابط</span>
        <button
          onClick={() => window.open(data.searchTerm, '_blank')}
          className="ml-auto text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
        >
          <ExternalLink size={12} />
          فتح
        </button>
      </div>
      <div className="p-4">
        <a
          href={data.searchTerm}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-400 hover:underline break-all"
        >
          {data.searchTerm}
        </a>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// عقدة الفيديو
function VideoNode({ data, selected }: NodeProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const videoUrl =
    data.searchTerm.includes('youtube') || data.searchTerm.includes('youtu.be')
      ? `https://www.youtube.com/embed/${extractYouTubeId(data.searchTerm)}`
      : data.searchTerm;

  return (
    <div
      className={`min-w-[400px] max-w-[600px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <Play size={16} className="text-red-400" />
        <span className="text-sm font-medium text-white">فيديو</span>
      </div>
      <div className="aspect-video bg-black">
        {isPlaying ? (
          <iframe
            src={videoUrl}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <button
            onClick={() => setIsPlaying(true)}
            className="w-full h-full flex items-center justify-center
                       bg-zinc-800 hover:bg-zinc-700 transition-colors"
          >
            <Play size={48} className="text-white/80" />
          </button>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

function extractYouTubeId(url: string): string {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([^&]+)/,
    /(?:youtu\.be\/)([^?]+)/,
    /(?:youtube\.com\/embed\/)([^/?]+)/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return url;
}

// عقدة الصورة
function ImageNode({ data, selected }: NodeProps) {
  const [loaded, setLoaded] = useState(false);
  return (
    <div
      className={`min-w-[250px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <ImageIcon size={16} className="text-green-400" />
        <span className="text-sm font-medium text-white">صورة</span>
      </div>
      <div className="p-2">
        <img
          src={data.searchTerm}
          alt="نتيجة البحث"
          onLoad={() => setLoaded(true)}
          className={`w-full rounded-lg transition-opacity ${loaded ? 'opacity-100' : 'opacity-0'}`}
          style={{ maxHeight: '400px', objectFit: 'cover' }}
        />
        {!loaded && (
          <div className="h-48 flex items-center justify-center bg-zinc-800 rounded-lg">
            <Loader2 size={24} className="animate-spin text-zinc-500" />
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// عقدة الموقع/الخريطة
function LocationNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`min-w-[350px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <MapPin size={16} className="text-red-400" />
        <span className="text-sm font-medium text-white">موقع</span>
      </div>
      <div className="h-48 bg-zinc-800 flex items-center justify-center">
        <div className="text-center">
          <MapPin size={32} className="text-zinc-600 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">خريطة تفاعلية</p>
          <p className="text-xs text-zinc-600 font-mono mt-1">{data.searchTerm}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// عقدة الملفات
function FileNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`min-w-[300px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <FileText size={16} className="text-yellow-400" />
        <span className="text-sm font-medium text-white">ملف</span>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 p-3 bg-zinc-800 rounded-lg">
          <FileText size={24} className="text-zinc-400" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{data.searchTerm}</p>
            <p className="text-xs text-zinc-500">ملف مرتبط بالمعرف</p>
          </div>
          <Download size={16} className="text-zinc-400 hover:text-white cursor-pointer" />
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// عقدة افتراضية
function DefaultNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`min-w-[300px] max-w-[500px] rounded-xl overflow-hidden
                  border transition-all
                  ${selected ? 'border-blue-500 shadow-lg shadow-blue-500/20' : 'border-zinc-700/80 shadow-xl shadow-black/50'}
                  bg-zinc-900/90 backdrop-blur-sm`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-800/50">
        <span className="text-xl">{data.detectedTypeIcon || '📄'}</span>
        <span className="text-sm font-medium text-white">
          {data.detectedTypeName || 'نتيجة بحث'}
        </span>
        <span className="text-xs text-zinc-500 ml-auto">
          {new Date(data.timestamp).toLocaleTimeString('ar-SA')}
        </span>
      </div>
      <div className="p-4 space-y-2">
        <p className="text-sm text-zinc-300 font-mono break-all">{data.searchTerm}</p>
        <p className="text-xs text-zinc-500">تم الكشف تلقائياً. اضغط لعرض التفاصيل الكاملة.</p>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

// سجل العقد المخصصة
const nodeTypes = {
  text: TextResultNode,
  link: LinkNode,
  video: VideoNode,
  image: ImageNode,
  location: LocationNode,
  file: FileNode,
  default: DefaultNode,
};

// ============================================================
// 6.3 اللوحة اللانهائية
// ============================================================

function InfiniteCanvas() {
  const { nodes: storeNodes, removeNode, updateNodePosition } = useInvestigationStore();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const reactFlowInstance = useReactFlow();

  // مزامنة العقد من المتجر إلى React Flow
  useEffect(() => {
    const flowNodes: Node[] = storeNodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
    }));
    setNodes(flowNodes);
  }, [storeNodes, setNodes]);

  // عند حذف عقدة من اللوحة
  const onNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      deletedNodes.forEach((node) => {
        removeNode(node.id);
      });
    },
    [removeNode]
  );

  // عند تحريك عقدة
  const onNodeDragStop = useCallback(
    (_event: any, node: Node) => {
      updateNodePosition(node.id, node.position);
    },
    [updateNodePosition]
  );

  const handleFitView = () => {
    reactFlowInstance.fitView({ padding: 0.2, duration: 500 });
  };

  const handleZoomIn = () => {
    reactFlowInstance.zoomIn({ duration: 300 });
  };

  const handleZoomOut = () => {
    reactFlowInstance.zoomOut({ duration: 300 });
  };

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodesDelete={onNodesDelete}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        deleteKeyCode={['Backspace', 'Delete']}
        multiSelectionKeyCode="Shift"
        selectionKeyCode="Shift"
        panOnDrag={[1, 2]}
        selectionOnDrag
        panActivationKeyCode="Space"
        className="bg-zinc-950"
        minZoom={0.1}
        maxZoom={4}
        defaultEdgeOptions={{
          style: { stroke: '#52525b', strokeWidth: 1 },
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={25}
          size={1.5}
          color="#27272a"
        />
        <Controls
          className="!bg-zinc-900 !border-zinc-700 !fill-zinc-400 !rounded-xl !overflow-hidden"
          showInteractive={false}
        />
        <MiniMap
          className="!bg-zinc-900 !border-zinc-700 !rounded-xl"
          maskColor="rgba(0,0,0,0.8)"
          nodeColor={(node) => {
            switch (node.type) {
              case 'video':
                return '#ef4444';
              case 'image':
                return '#22c55e';
              case 'link':
                return '#3b82f6';
              case 'location':
                return '#f59e0b';
              case 'file':
                return '#eab308';
              default:
                return '#71717a';
            }
          }}
          pannable
          zoomable
        />
        <Panel position="top-right" className="flex gap-1">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-zinc-900/80 border border-zinc-700 rounded-lg
                       text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
            title="تكبير"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-zinc-900/80 border border-zinc-700 rounded-lg
                       text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
            title="تصغير"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={handleFitView}
            className="p-2 bg-zinc-900/80 border border-zinc-700 rounded-lg
                       text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
            title="احتواء الكل"
          >
            <Maximize2 size={16} />
          </button>
        </Panel>
      </ReactFlow>
    </div>
  );
}

// ============================================================
// 6.4 صفحة غرفة التحري (المكون الرئيسي)
// ============================================================

export default function InvestigatePage() {
  const router = useRouter();
  const { nodes, addNode, clearAllNodes } = useInvestigationStore();

  const handleSearch = useCallback(
    (node: InvestigationNode) => {
      addNode(node);
    },
    [addNode]
  );

  const handleClearAll = () => {
    if (nodes.length === 0) return;
    if (window.confirm('هل أنت متأكد من مسح جميع النتائج؟')) {
      clearAllNodes();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="fixed inset-0 z-[100] bg-zinc-950 flex flex-col"
    >
      {/* الشريط العلوي */}
      <header className="h-16 border-b border-zinc-800 flex items-center gap-4 px-4 bg-zinc-950/80 backdrop-blur-md">
        <button
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-2 text-zinc-400 hover:text-white
                     transition-colors text-sm group"
        >
          <ArrowLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
          <span className="hidden sm:inline">العودة لغرفة القيادة</span>
        </button>

        <div className="flex-1 flex justify-center">
          <SearchBar onSearch={handleSearch} />
        </div>

        <div className="flex items-center gap-2">
          {nodes.length > 0 && (
            <>
              <span className="text-xs text-zinc-500 hidden sm:inline">
                {nodes.length} نتيجة
              </span>
              <button
                onClick={handleClearAll}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg
                           text-xs text-zinc-500 hover:text-red-400
                           hover:bg-red-500/10 border border-transparent hover:border-red-500/30
                           transition-all"
              >
                <Trash2 size={14} />
                <span className="hidden sm:inline">مسح الكل</span>
              </button>
            </>
          )}
          {nodes.length === 0 && (
            <span className="text-xs text-zinc-600 hidden sm:inline">
              اكتب أو ألصق معرفاً للبدء
            </span>
          )}
        </div>
      </header>

      {/* اللوحة اللانهائية */}
      <main className="flex-1 relative">
        {nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <div className="text-6xl mb-4 opacity-30">✦</div>
              <p className="text-zinc-500 text-lg">غرفة التحري جاهزة</p>
              <p className="text-zinc-600 text-sm mt-2">
                اكتب أو ألصق أي معرف في حقل البحث للبدء
              </p>
              <p className="text-zinc-700 text-xs mt-4 max-w-md">
                يدعم أكثر من 500 نوع معرف: بريد إلكتروني، MAC، IMEI، UUID،
                عناوين بلوكتشين، معرفات اجتماعية، والمزيد...
              </p>
            </div>
          </div>
        ) : (
          <ReactFlowProvider>
            <InfiniteCanvas />
          </ReactFlowProvider>
        )}
      </main>
    </motion.div>
  );
}

// ============================================================
// 7. زر الدخول إلى غرفة التحري
// المسار: src/components/CommandCenter/InvestigateButton.tsx
// هذا الزر يوضع في غرفة القيادة (الصفحة الرئيسية)
// ============================================================

export function InvestigateButton() {
  const router = useRouter();
  const { nodes } = useInvestigationStore();

  return (
    <motion.button
      onClick={() => router.push('/investigate')}
      className="fixed bottom-6 right-6 z-50
                 flex items-center gap-2
                 px-4 py-3 rounded-2xl
                 bg-zinc-900/90 backdrop-blur-md
                 border border-zinc-700/80
                 text-white
                 shadow-2xl shadow-black/50
                 hover:scale-105 hover:bg-zinc-800
                 active:scale-95
                 transition-all group"
      whileHover={{ boxShadow: '0 0 40px rgba(255,255,255,0.1)' }}
      title="غرفة التحري"
    >
      <span className="text-xl">✦</span>
      <span className="text-sm font-medium hidden sm:inline">غرفة التحري</span>
      {nodes.length > 0 && (
        <span className="bg-blue-500 text-white text-xs rounded-full
                         w-5 h-5 flex items-center justify-center
                         absolute -top-1 -right-1">
          {nodes.length > 99 ? '99+' : nodes.length}
        </span>
      )}
    </motion.button>
  );
}

// ============================================================
// نهاية الكود
// ============================================================
// هيكل المجلدات المطلوب:
// src/
// ├── app/
// │   ├── dashboard/
// │   │   └── page.tsx          ← غرفة القيادة (الرئيسية)
// │   └── investigate/
// │       └── page.tsx           ← غرفة التحري (هذا الملف)
// ├── components/
// │   └── CommandCenter/
// │       └── InvestigateButton.tsx  ← زر الدخول للغرفة
// ├── store/
// │   └── investigationStore.ts     ← حالة زوستاند
// ├── types/
// │   └── investigation.ts          ← الأنواع
// └── utils/
//     ├── identifierList.ts         ← قائمة المعرفات + كاشف
//     └── fuzzySearch.ts            ← البحث الغامض
//
// تثبيت المكتبات المطلوبة:
// npm install zustand zod fuse.js framer-motion reactflow
// npm install lucide-react  (للأيقونات)
// ============================================================
