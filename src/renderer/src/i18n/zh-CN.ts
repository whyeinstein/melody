/**
 * 渲染层界面文案（简体中文）。
 *
 * 约定：所有用户可见文字都必须从这里取，组件里不写死中文字符串，
 * 后续接入多语言时只需要增加语言包并替换这个模块的导出即可。
 */
export const zhCN = {
  app: {
    name: 'Melody',
    tagline: '本地音乐库',
    booting: '正在启动…',
    stage: '阶段 1 · 音乐库与播放核心',
    version: (version: string): string => `版本 ${version}`
  },

  nav: {
    libraryGroup: '音乐库',
    songs: '歌曲',
    albums: '专辑',
    artists: '艺术家',
    genres: '流派',
    folders: '文件夹',
    recent: '最近添加',
    favorites: '我喜欢',
    playlists: '播放列表'
  },

  common: {
    loading: '加载中…',
    retry: '重试',
    refresh: '刷新',
    close: '关闭',
    cancel: '取消',
    clear: '清空',
    remove: '移除',
    more: '更多操作',
    comingSoon: '即将推出',
    unknownArtist: '未知艺术家',
    unknownAlbum: '未知专辑',
    noData: '暂无数据',
    count: (total: number): string => `${total} 首`,
    albumCount: (count: number): string => `${count} 张专辑`,
    artistCount: (count: number): string => `${count} 位艺术家`,
    genreCount: (count: number): string => `${count} 个流派`,
    folderCount: (count: number): string => `${count} 个文件夹`,
    playlistCount: (count: number): string => `${count} 个播放列表`
  },

  actions: {
    play: '播放',
    pause: '暂停',
    next: '下一首',
    previous: '上一首',
    playAll: '播放全部',
    addToQueue: '添加到队列',
    playNext: '下一首播放',
    removeFromQueue: '从队列移除',
    addFavorite: '添加到「我喜欢」',
    removeFavorite: '从「我喜欢」移除'
  },

  player: {
    nothingPlaying: '未在播放',
    nowPlaying: '正在播放',
    shuffleOn: '随机播放：开',
    shuffleOff: '随机播放：关',
    repeatOff: '循环：关闭',
    repeatAll: '列表循环',
    repeatOne: '单曲循环',
    volume: '音量',
    mute: '静音',
    unmute: '取消静音',
    queue: '播放队列',
    progress: '播放进度'
  },

  queue: {
    title: '播放队列',
    close: '关闭播放队列',
    empty: '队列是空的',
    emptyHint: '在歌曲列表里点击任意歌曲即可开始播放。',
    nowPlaying: '正在播放',
    clear: '清空队列',
    dragHint: '拖拽可调整队列顺序',
    count: (total: number): string => `${total} 首歌曲`,
    position: (current: number, total: number): string => `${current} / ${total}`
  },

  columns: {
    index: '#',
    title: '标题',
    artist: '艺术家',
    album: '专辑',
    duration: '时长',
    favorite: '收藏'
  },

  views: {
    songs: '歌曲',
    albums: '专辑',
    artists: '艺术家',
    genres: '流派',
    folders: '音乐文件夹',
    recent: '最近添加',
    favorites: '我喜欢',
    playlists: '播放列表'
  },

  library: {
    loadFailed: '加载音乐库失败',
    emptyTitle: '音乐库还是空的',
    emptyHint: '先在「文件夹」中添加音乐目录，然后开始扫描，歌曲会出现在这里。',
    emptySearch: '没有找到匹配的歌曲',
    emptySearchHint: (keyword: string): string => `没有与「${keyword}」匹配的结果，试试其他关键词。`,
    emptyFavorites: '还没有喜欢的歌曲',
    emptyFavoritesHint: '点击歌曲右侧的心形图标，收藏的歌曲会出现在这里。',
    emptyRecent: '还没有最近添加的歌曲',
    emptyRecentHint: '扫描音乐库后，最新入库的歌曲会按时间倒序排列。',
    emptyAlbums: '还没有专辑',
    emptyAlbumsHint: '扫描音乐库后，这里会按专辑聚合显示。',
    emptyArtists: '还没有艺术家',
    emptyArtistsHint: '扫描音乐库后，这里会按艺术家聚合显示。',
    emptyGenres: '还没有流派',
    emptyGenresHint: '扫描音乐库后，这里会按流派聚合显示。',
    emptyPlaylists: '还没有播放列表',
    emptyPlaylistsHint: '播放列表功能将在阶段 2 开放。',
    channelNotReady: '该功能尚未就绪',
    channelNotReadyHint: '主进程中的相关频道还未实现，界面已做降级处理，不会影响其他功能。',
    refreshDone: '音乐库数据已刷新',
    scanIdle: '尚未扫描',
    scanScanning: '正在扫描音乐库…',
    scanDone: '扫描完成',
    scanCancelled: '扫描已取消',
    scanError: '扫描失败',
    scanningPath: (path: string): string => `正在解析：${path}`,
    scanSummary: (added: number, updated: number): string => `新增 ${added} 首 · 更新 ${updated} 首`,
    scanCounters: (visited: number, parsed: number, failed: number): string =>
      `已访问 ${visited} · 已解析 ${parsed} · 失败 ${failed}`,
    startScan: '开始扫描',
    cancelScan: '取消扫描',
    addFolder: '添加文件夹',
    removeFolder: '移除文件夹',
    folderDisabled: '已停用',
    foldersTitle: '音乐文件夹',
    foldersHint: 'Melody 会扫描这些目录下的音频文件。',
    foldersEmpty: '还没有音乐文件夹',
    foldersEmptyHint: '添加本地音乐目录后即可扫描入库。',
    playlistsHint: '手动播放列表将在后续阶段支持创建与编辑。',
    totalTracks: (total: number): string => `${total} 首歌曲`,
    shownTracks: (shown: number, total: number): string => `显示 ${shown} / ${total} 首`
  },

  errors: {
    generic: '操作失败',
    bridgeMissing: '预加载桥接不可用（window.melody 缺失）',
    channelNotReady: '主进程功能尚未就绪',
    playbackFailed: '播放失败',
    mediaUnavailable: '音频服务未就绪',
    mediaUnavailableHint: '主进程的媒体服务（media:session）尚未实现，暂时无法播放本地音频。',
    trackLoadFailed: '无法加载音频',
    loadAudioFailed: '音频加载失败，格式可能不受支持',
    mediaAborted: '音频加载被中断',
    mediaNetwork: '音频网络请求失败',
    mediaDecode: '音频解码失败，格式可能不受支持',
    rootContainer: '找不到 #root 容器',
    favoriteFailed: '收藏操作失败',
    folderAddFailed: '添加文件夹失败',
    folderRemoveFailed: '移除文件夹失败',
    folderChooseFailed: '选择文件夹失败',
    scanStartFailed: '启动扫描失败',
    configUnavailable: '配置服务未就绪，部分偏好设置无法保存',
    noTrackSelected: '队列里还没有歌曲',
    queueEnded: '队列已播放完毕'
  },

  toasts: {
    favoriteAdded: '已添加到「我喜欢」',
    favoriteRemoved: '已从「我喜欢」移除',
    addedToQueue: '已加入播放队列',
    willPlayNext: '将在下一首播放',
    alreadyInQueue: '歌曲已在队列中',
    queueCleared: '播放队列已清空',
    foldersAdded: (count: number): string => `已添加 ${count} 个音乐文件夹`,
    scanStarted: '开始扫描音乐库',
    scanCancelled: '已取消扫描'
  },

  command: {
    title: '命令面板',
    placeholder: '输入命令或搜索…',
    hint: '命令面板为占位实现：输入框暂不执行命令，阶段 2 将接入全局搜索与操作。',
    shortcutsTitle: '键盘快捷键'
  },

  shortcuts: {
    space: '播放 / 暂停',
    seek: '快退 / 快进 5 秒',
    search: '聚焦搜索',
    palette: '打开命令面板',
    escape: '关闭浮层'
  },

  search: {
    placeholder: '搜索歌曲、专辑或艺术家',
    clear: '清空搜索',
    label: '搜索音乐库'
  },

  status: {
    storageOk: (engine: string): string => `存储 ${engine}`,
    storageUnavailable: '存储不可用',
    ffmpegFound: 'ffmpeg 已就绪',
    ffmpegMissing: 'ffmpeg 未找到',
    dataPath: '数据目录',
    appInfoFailed: '读取运行环境失败'
  },

  time: {
    /** 专辑/播放列表总时长。 */
    duration: (hours: number, minutes: number): string => {
      if (hours <= 0) return `${minutes} 分钟`
      return minutes === 0 ? `${hours} 小时` : `${hours} 小时 ${minutes} 分钟`
    }
  }
} as const
