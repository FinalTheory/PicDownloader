# PicDownloader: 功能强大的图片数据定时下载平台


## 运行

首先将编译好的压缩包解压，并进入对应文件夹，包含的文件如下：

![文件列表](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/1.png)

其中重要文件有：

- **Main.exe:** 主程序文件，用于启动下载平台；
- **config.ini:** 全局配置文件，其中包含所有全局设置；
- **data.db:** 数据库文件，用于存放所有用户数据，如自定义的下载规则等；
- **test_webfunc.exe:** 单元测试程序，用于检查该软件在操作系统上是否能够正常运行。

双击**Main.exe**来启动平台，其运行界面如下：

![运行示例](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/2.png)

打开浏览器，输入本机的公网IP地址，或者`localhsot`，即可进入平台登录界面：

![平台首页](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/3.png)

登录后进入管理页面：

![管理页面](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/4.png)

下面简单介绍各个页面的具体功能。


## 添加规则

![添加规则](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/5.png)

简单解释一下上图中各个选项的含义：

- **规则名称：**可以为每条规则指定一个有意义的名称，以便于区分。
- **保存位置：**一般留空即可，如果非空，那么系统会在当前用户文件夹下创建一个以此命名的子目录，并将这条规则所下载的文件都存放在该子目录中，起到一个分类的效果。
- **规则链接：**需要定时下载的文件链接。其中可以包含日期变量。
- **插入变量：**用于插入特定格式的日期变量。
- **定时执行：**这里设置定时执行的方式，很容易理解。
- **任务时区：**系统支持将定时执行的时间设置为相对于特定时区的时间。例如，如果指定每天12:00开始执行下载，并将任务时区设置为UTC时区，那么任务将会在每天的UTC时间12:00，也就是北京时间20:00开始下载。

### 时间变量



### 规则示例

以定时下载中央气象台的卫星云图为例，我们需要添加如下两条规则：

**UTC时间 17:00 以后**
`http://image.nmc.cn/product/%year@Asia/Shanghai#-1%/%year@Asia/Shanghai#-1%%mon@Asia/Shanghai#-1%/%year@Asia/Shanghai#-1%%mon@Asia/Shanghai#-1%%day@Asia/Shanghai#-1%/WXCL/SEVP_NSMC_WXCL_ASC_E99_ACHN_LNO_PY_%year@UTC#0%%mon@UTC#0%%day@UTC#0%{0000|0015|0030|0045|0100|0115|0130|0145|0200|0215|0230|0245|0300|0315|0330|0345|0400|0415|0430|0445|0500|0515|0530|0545|0600|0615|0630|0645|0700|0715|0730|0745|0800|0815|0830|0845|0900|0915|0930|0945|1000|1015|1030|1045|1100|1115|1130|1145|1200|1215|1230|1245|1300|1315|1330|1345|1400|1415|1430|1445|1500|1515|1530|1545}00000.JPG`

**UTC时间 01:00 以后**
`http://image.nmc.cn/product/%year@Asia/Shanghai#0%/%year@Asia/Shanghai#0%%mon@Asia/Shanghai#0%/%year@Asia/Shanghai#0%%mon@Asia/Shanghai#0%%day@Asia/Shanghai#0%/WXCL/SEVP_NSMC_WXCL_ASC_E99_ACHN_LNO_PY_%year@UTC#-1%%mon@UTC#-1%%day@UTC#-1%{1600|1615|1630|1645|1700|1715|1730|1745|1800|1815|1830|1845|1900|1915|1930|1945|2000|2015|2030|2045|2100|2115|2130|2145|2200|2215|2230|2245|2300|2315|2330|2345}00000.JPG`

其中形如`http://example.com/{a|b|c}.jpg`的用法是指，这条规则将在开始下载时一次性生成如下三个下载链接，并分别进行下载：

- `http://example.com/a.jpg`
- `http://example.com/b.jpg`
- `http://example.com/c.jpg`

这样的设计使得我们可以使用一条规则来定时下载多个文件。

**注意，一条规则链接中只能包含一个形如`{a|b|c}`的部分！**


## 任务查询

![添加规则](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/7.png)

这个界面主要用于查看当前进入下载时间的任务以及其状态。


## 查看日志

![查看日志](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/8.png)

日志系统记录了发生的所有重要事件，以供使用者检查软件的运行状态。注意日志是倒序排序的，并且由于日志数量可能会较多，因此不会完全显示出来。可以在“系统管理”中设置最大的日志显示数量，默认为显示128条。


## 个人设置

![个人设置](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/9.png)

这里记录了一些个人信息，需要输入原密码（不管是否修改密码）才能够修改个人设置。

每个用户所能够下载的最大文件数量以及可以占用的最大磁盘空间是有限制并且可以设置的，以免文件占满硬盘，影响其他任务的进行。如果某个用户已经超出了配额限制，那么就会**自动地删除最老的那些文件，直至低于配额**。当然，这个功能可以关闭，方法是编辑`config.ini`，设置`disk_quota = false`。


## 系统管理

![系统管理](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/example/6.png)

这里主要是一些与系统运行相关的设置选项，比如各个检查时间间隔等，一般不需要修改。例如，“磁盘配额检查间隔”是指，每隔特定的时间，系统会扫描所有用户的下载文件，并检查是否超出配额。由于这个检查功能较为占用系统资源，因此每隔较长的一段时间才会运行一次。


## 编译[Windows平台]

安装所有相关依赖库，进入源代码目录，运行：

> `python setup.py py2exe`


## FAQ

### 该平台的运行原理是怎样的？

请参考[分布式数据下载系统的设计与实现](https://raw.githubusercontent.com/FinalTheory/PicDownloader/primitive/data-download-system.pdf)这篇论文，其中给出了详细的技术选型与系统设计思路。

