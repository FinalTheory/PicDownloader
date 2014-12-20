CREATE TABLE `UserTask` (
	`TaskID`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`UID`	TEXT NOT NULL,
	`URL_Rule`	TEXT NOT NULL,
	`Rule_Name`	TEXT NOT NULL,
	`RepeatType`	INTEGER NOT NULL,
	`RepeatValue`	TEXT NOT NULL,
	`TimeZone`	TEXT NOT NULL,
	`Status`	INTEGER NOT NULL
);

CREATE TABLE `CurrentTask` (
	`UID`	TEXT NOT NULL,
	`URL`	TEXT NOT NULL,
	`Status`	INTEGER NOT NULL,
	`Location`	TEXT NOT NULL,
	`StartTime`	TEXT NOT NULL,
	`FinishTime`	TEXT NOT NULL,
	PRIMARY KEY(UID)
);

CREATE TABLE `Users` (
	`UID`	TEXT NOT NULL UNIQUE,
	`SessionID`	TEXT,
	`UserStatus`	INTEGER NOT NULL,
	`UserName`	TEXT NOT NULL,
	`PassWord`	TEXT NOT NULL,
	`Tel`	TEXT NOT NULL,
	`E-mail`	TEXT NOT NULL,
	`MaxSize`	INTEGER NOT NULL,
	`MaxFiles`	INTEGER NOT NULL,
	`Downloader`	TEXT NOT NULL,
	`NameRule`	TEXT NOT NULL DEFAULT 'default',
	PRIMARY KEY(UID)
);

INSERT INTO `Users`(`UID`,`SessionID`,`UserStatus`,`UserName`,`PassWord`,`Tel`,`E-mail`,`MaxSize`,`MaxFiles`,`Downloader`) VALUES ('root',NULL,0,'Admin','3.1415926','','',1024,1024,'aria2');