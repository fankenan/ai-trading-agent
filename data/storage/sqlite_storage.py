# -*- coding: utf-8 -*-
"""
SQLite数据存储模块

提供基于SQLite的本地数据持久化功能，支持K线数据和市场快照的存储与查询。
自动创建数据库表和索引，确保数据读写效率。
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger


class SQLiteStorage:
    """SQLite数据存储引擎

    负责K线数据和市场快照的本地持久化存储，支持按时间范围查询、
    获取最新时间戳和清理过期数据。

    Attributes:
        db_path: SQLite数据库文件路径
    """

    def __init__(self, db_path: str = "data/trading.db") -> None:
        """初始化SQLite存储引擎

        Args:
            db_path: 数据库文件路径，默认为 "data/trading.db"
        """
        self.db_path: str = db_path
        self.conn: sqlite3.Connection = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info("SQLite存储引擎初始化完成: db_path={}", db_path)

    def _create_tables(self) -> None:
        """创建数据库表和索引

        创建以下表结构：
        - klines: K线数据表，按(symbol, interval, timestamp)建立唯一索引
        - snapshots: 市场快照表，按timestamp建立索引
        """
        cursor = self.conn.cursor()

        # 创建K线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, interval, timestamp)
            )
        """)

        # 创建K线数据索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_interval
            ON klines(symbol, interval)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_klines_timestamp
            ON klines(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_interval_timestamp
            ON klines(symbol, interval, timestamp)
        """)

        # 创建市场快照表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT,
                price REAL,
                change_percent REAL,
                high REAL,
                low REAL,
                volume REAL,
                amount REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建快照索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_symbol
            ON snapshots(symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
            ON snapshots(timestamp)
        """)

        self.conn.commit()
        logger.debug("数据库表和索引创建/验证完成")

    def save_klines(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
    ) -> int:
        """保存K线数据到数据库

        将DataFrame中的K线数据批量插入数据库，遇到重复记录时跳过。

        Args:
            df: K线数据DataFrame，需包含列:
                [timestamp, open, high, low, close, volume]
            symbol: 币种符号，如 "btc"
            interval: K线周期，如 "daily"、"hourly"

        Returns:
            成功插入的记录数
        """
        if df is None or df.empty:
            logger.warning("保存K线数据跳过: DataFrame为空")
            return 0

        logger.info(
            "保存K线数据: symbol={}, interval={}, 记录数={}",
            symbol,
            interval,
            len(df),
        )

        cursor = self.conn.cursor()
        inserted_count: int = 0

        try:
            for _, row in df.iterrows():
                try:
                    # 解析时间戳
                    timestamp = pd.Timestamp(row["timestamp"])
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

                    cursor.execute("""
                        INSERT OR IGNORE INTO klines
                        (symbol, interval, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        interval,
                        timestamp_str,
                        float(row.get("open", 0)),
                        float(row.get("high", 0)),
                        float(row.get("low", 0)),
                        float(row.get("close", 0)),
                        float(row.get("volume", 0)),
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += 1
                except (ValueError, TypeError) as e:
                    logger.warning("跳过无效K线记录: {}", e)
                    continue

            self.conn.commit()
            logger.info(
                "K线数据保存完成: symbol={}, interval={}, 插入={}, 跳过={}",
                symbol,
                interval,
                inserted_count,
                len(df) - inserted_count,
            )
            return inserted_count

        except Exception as e:
            self.conn.rollback()
            logger.error("保存K线数据失败: {}", e)
            raise

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """从数据库查询K线数据

        支持按时间范围和记录数量限制查询K线数据。

        Args:
            symbol: 币种符号，如 "btc"
            interval: K线周期，如 "daily"、"hourly"
            start_time: 起始时间，格式 "YYYY-MM-DD HH:MM:SS"
            end_time: 结束时间，格式 "YYYY-MM-DD HH:MM:SS"
            limit: 最大返回记录数，None表示不限制

        Returns:
            K线数据DataFrame，列名:
            [timestamp, open, high, low, close, volume]
        """
        logger.info(
            "查询K线数据: symbol={}, interval={}, start={}, end={}, limit={}",
            symbol,
            interval,
            start_time,
            end_time,
            limit,
        )

        query: str = """
            SELECT timestamp, open, high, low, close, volume
            FROM klines
            WHERE symbol = ? AND interval = ?
        """
        params: List[Any] = [symbol, interval]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp ASC"

        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        try:
            df = pd.read_sql_query(query, self.conn, params=params)

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                numeric_columns = ["open", "high", "low", "close", "volume"]
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info(
                "K线数据查询完成: symbol={}, interval={}, 记录数={}",
                symbol,
                interval,
                len(df),
            )
            return df

        except Exception as e:
            logger.error("查询K线数据失败: {}", e)
            raise

    def get_latest_timestamp(
        self,
        symbol: str,
        interval: str,
    ) -> Optional[pd.Timestamp]:
        """获取指定币种和周期的最新K线时间戳

        用于增量数据更新时确定数据同步的起点。

        Args:
            symbol: 币种符号，如 "btc"
            interval: K线周期，如 "daily"、"hourly"

        Returns:
            最新K线时间戳，如果没有数据则返回None
        """
        logger.debug("获取最新时间戳: symbol={}, interval={}", symbol, interval)

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT MAX(timestamp) as latest
                FROM klines
                WHERE symbol = ? AND interval = ?
            """, (symbol, interval))

            row = cursor.fetchone()
            if row and row["latest"]:
                latest_ts = pd.Timestamp(row["latest"])
                logger.debug(
                    "最新时间戳: symbol={}, interval={}, latest={}",
                    symbol,
                    interval,
                    latest_ts,
                )
                return latest_ts

            logger.debug(
                "无历史数据: symbol={}, interval={}", symbol, interval
            )
            return None

        except Exception as e:
            logger.error("获取最新时间戳失败: {}", e)
            raise

    def save_snapshot(self, snapshot: Dict[str, Dict[str, object]]) -> int:
        """保存市场快照到数据库

        将多个币种的实时行情快照批量保存到数据库。

        Args:
            snapshot: 市场快照字典，key为币种符号，
                      value为行情字典（包含price, change_percent等字段）

        Returns:
            成功插入的记录数
        """
        if not snapshot:
            logger.warning("保存市场快照跳过: 快照数据为空")
            return 0

        logger.info("保存市场快照: 币种数={}", len(snapshot))

        cursor = self.conn.cursor()
        inserted_count: int = 0

        try:
            for symbol, quote in snapshot.items():
                if not quote:
                    continue

                try:
                    cursor.execute("""
                        INSERT INTO snapshots
                        (symbol, name, price, change_percent, high, low, volume, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        str(quote.get("name", "")),
                        float(quote.get("price", 0)),
                        float(quote.get("change_percent", 0)),
                        float(quote.get("high", 0)),
                        float(quote.get("low", 0)),
                        float(quote.get("volume", 0)),
                        float(quote.get("amount", 0)),
                    ))
                    inserted_count += 1
                except (ValueError, TypeError) as e:
                    logger.warning("跳过无效快照记录: symbol={}, error={}", symbol, e)
                    continue

            self.conn.commit()
            logger.info(
                "市场快照保存完成: 插入={}条", inserted_count
            )
            return inserted_count

        except Exception as e:
            self.conn.rollback()
            logger.error("保存市场快照失败: {}", e)
            raise

    def delete_old_data(self, days: int = 90) -> int:
        """删除指定天数之前的旧数据

        清理K线数据表和市场快照表中的过期数据，释放存储空间。

        Args:
            days: 保留最近多少天的数据，默认90天

        Returns:
            删除的总记录数
        """
        if days <= 0:
            raise ValueError(f"保留天数必须大于0，当前值: {days}")

        cutoff_time = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        logger.info("清理旧数据: 保留最近{}天, 截止时间={}", days, cutoff_time)

        cursor = self.conn.cursor()
        total_deleted: int = 0

        try:
            # 删除旧K线数据
            cursor.execute(
                "DELETE FROM klines WHERE timestamp < ?", (cutoff_time,)
            )
            klines_deleted = cursor.rowcount
            total_deleted += klines_deleted

            # 删除旧快照数据
            cursor.execute(
                "DELETE FROM snapshots WHERE timestamp < ?", (cutoff_time,)
            )
            snapshots_deleted = cursor.rowcount
            total_deleted += snapshots_deleted

            # 压缩数据库释放空间
            self.conn.execute("VACUUM")

            logger.info(
                "旧数据清理完成: K线删除{}条, 快照删除{}条, 总计{}条",
                klines_deleted,
                snapshots_deleted,
                total_deleted,
            )
            return total_deleted

        except Exception as e:
            self.conn.rollback()
            logger.error("清理旧数据失败: {}", e)
            raise

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def __del__(self) -> None:
        """析构函数，确保数据库连接关闭"""
        try:
            self.close()
        except Exception:
            pass
