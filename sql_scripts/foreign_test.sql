DROP TABLE IF EXISTS album;
DROP TABLE IF EXISTS song;

CREATE TABLE album(
  albumartist TEXT,
  PRIMARY KEY(albumartist)
);

CREATE TABLE song(
  songartist TEXT,
  FOREIGN KEY(songartist) REFERENCES album(albumartist)
);
