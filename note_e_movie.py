"""
Note-E-Movie - Personal Movie & Series Collection Manager
A comprehensive desktop application for managing your entertainment library
Dark Mode Interface with Enhanced Security and Content Management
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import shutil
import logging
from typing import Optional, List, Dict, Any, Union

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QTableWidget, QTableWidgetItem, QHeaderView, 
                              QPushButton, QLineEdit, QComboBox, QLabel, 
                              QDialog, QFormLayout, QSpinBox, QDoubleSpinBox,
                              QMessageBox, QFileDialog, QStatusBar, QFrame,
                              QSplitter, QGroupBox, QGridLayout, QToolBar,
                              QMenuBar, QMenu, QTextEdit, QTabWidget,
                              QCheckBox, QScrollArea)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QThread
from PySide6.QtGui import QIcon, QFont, QAction, QPalette, QColor, QPixmap


# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('note_e_movie.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Data Classes

class MediaItem:
    """Base class for movies and series with validation and security"""
    
    def __init__(self, title: str, year: Union[str, int], rating: float, 
                 content_flags: Optional[Dict[str, float]] = None):
        self.title = self._sanitize_string(title)
        self.year = self._parse_year(year)
        self.rating = self._validate_rating(rating)
        self.content_flags = content_flags or {}
        self.date_added = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Created {self.__class__.__name__}: {self.title}")
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input for security"""
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")
        
        # Remove potential harmful characters
        sanitized = str(value).strip()
        if not sanitized:
            raise ValueError("Title cannot be empty")
        
        # Basic XSS prevention
        dangerous_chars = ['<', '>', '"', "'", '&']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized
    
    def _parse_year(self, year: Union[str, int]) -> str:
        """Parse and validate year input"""
        if isinstance(year, str):
            # Handle ranges like "2008-13" or "1994-04"
            if '-' in year:
                return year
            try:
                year_int = int(year)
                if 1800 <= year_int <= datetime.now().year + 5:
                    return str(year_int)
                else:
                    raise ValueError(f"Year out of range: {year_int}")
            except ValueError:
                raise ValueError(f"Invalid year format: {year}")
        
        if isinstance(year, int):
            if 1800 <= year <= datetime.now().year + 5:
                return str(year)
            else:
                raise ValueError(f"Year out of range: {year}")
        
        raise ValueError(f"Invalid year type: {type(year)}")
    
    def _validate_rating(self, rating: float) -> float:
        """Validate rating input"""
        if pd.isna(rating):
            return 0.0
        
        try:
            rating_float = float(rating)
            if 0 <= rating_float <= 11:  # Allow up to 11 as seen in data
                return rating_float
            else:
                raise ValueError(f"Rating must be between 0 and 11: {rating_float}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid rating value: {rating}, defaulting to 0.0")
            return 0.0
    
    def get_content_warnings(self) -> List[str]:
        """Get content warning flags"""
        warnings = []
        warning_mapping = {
            'Romantic': 'Romance',
            'Comedy': 'Comedy',
            'Action': 'Action',
            'Intimacy': 'Intimate Scenes',
            'Abusive': 'Violence/Abuse',
            'Naked': 'Nudity'
        }
        
        for key, label in warning_mapping.items():
            if key in self.content_flags and self.content_flags[key] > 0:
                level = self.content_flags[key]
                warnings.append(f"{label} ({level}/5)")
        
        return warnings


class Movie(MediaItem):
    """Movie data class with enhanced validation"""
    
    def __init__(self, title: str, year: Union[str, int], rating: float, 
                 genre: str = "Unknown", status: str = "Watched",
                 content_flags: Optional[Dict[str, float]] = None, comments: str = ""):
        super().__init__(title, year, rating, content_flags)
        self.genre = self._sanitize_string(genre) if genre else "Unknown"
        self.status = status if status in ['Watched', 'Plan to Watch'] else 'Watched'
        self.comments = self._sanitize_string(comments) if comments else ""
        self.media_type = "Movie"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert movie to dictionary"""
        return {
            'Title': self.title,
            'Year': self.year,
            'Rating': self.rating,
            'Genre': self.genre,
            'Status': self.status,
            'Comments': self.comments,
            'Content Flags': self.content_flags,
            'Date Added': self.date_added,
            'Type': self.media_type
        }
    
    @classmethod
    def from_excel_row(cls, row: pd.Series) -> 'Movie':
        """Create movie from Excel row"""
        content_flags = {}
        flag_columns = ['Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
        
        for col in flag_columns:
            if col in row and pd.notna(row[col]):
                content_flags[col] = float(row[col])
        
        return cls(
            title=row.get('Movie Name', ''),
            year=row.get('Release Year', 2000),
            rating=row.get('Rating on 1-10', 0.0),
            content_flags=content_flags,
            comments=row.get('Comments', '')
        )
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'Movie':
        """Create movie from CSV row"""
        content_flags = {}
        flag_columns = ['Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
        
        for col in flag_columns:
            if col in row and pd.notna(row[col]):
                content_flags[col] = float(row[col])
        
        return cls(
            title=row.get('Title', ''),
            year=row.get('Year', 2000),
            rating=row.get('Rating', 0.0),
            content_flags=content_flags,
            comments=row.get('Comments', '')
        )


class Series(MediaItem):
    """TV Series data class with season tracking"""
    
    def __init__(self, title: str, years: str, rating: float,
                 seasons: float = 0.0, episodes_watched: int = 0,
                 family_friendly: bool = True, genre: str = "Unknown",
                 language: str = "English", content_flags: Optional[Dict[str, float]] = None,
                 comments: str = ""):
        super().__init__(title, years, rating, content_flags)
        self.years = years  # Keep original year range format
        self.seasons = float(seasons) if pd.notna(seasons) else 0.0
        self.episodes_watched = int(episodes_watched) if episodes_watched else 0
        self.family_friendly = self._determine_family_friendly(content_flags or {})
        self.genre = self._sanitize_string(genre) if genre else "Unknown"
        self.language = self._sanitize_string(language) if language else "English"
        self.comments = self._sanitize_string(comments) if comments else ""
        self.media_type = "Series"
    
    def _determine_family_friendly(self, content_flags: Dict[str, float]) -> bool:
        """Determine if series is family-friendly based on content flags"""
        if not content_flags:
            return True
        
        risky_content = ['Intimacy', 'Abusive', 'Naked']
        for flag in risky_content:
            if flag in content_flags and content_flags[flag] > 2:
                return False
        
        return True
    
    def get_start_year(self) -> int:
        """Extract start year from years range"""
        try:
            if '-' in self.years:
                return int(self.years.split('-')[0])
            return int(self.years)
        except:
            return 2000
    
    def get_end_year(self) -> Optional[int]:
        """Extract end year from years range"""
        try:
            if '-' in self.years:
                end_part = self.years.split('-')[1]
                if len(end_part) == 2:  # Handle format like "2008-13"
                    start_year = self.get_start_year()
                    century = (start_year // 100) * 100
                    return century + int(end_part)
                return int(end_part)
            return None
        except:
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert series to dictionary"""
        return {
            'Title': self.title,
            'Years': self.years,
            'Start Year': self.get_start_year(),
            'End Year': self.get_end_year(),
            'Rating': self.rating,
            'Seasons': self.seasons,
            'Episodes Watched': self.episodes_watched,
            'Family Friendly': self.family_friendly,
            'Genre': self.genre,
            'Language': self.language,
            'Comments': self.comments,
            'Content Flags': self.content_flags,
            'Date Added': self.date_added,
            'Type': self.media_type
        }
    
    @classmethod
    def from_excel_row(cls, row: pd.Series) -> 'Series':
        """Create series from Excel row"""
        content_flags = {}
        flag_columns = ['Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
        
        for col in flag_columns:
            if col in row and pd.notna(row[col]):
                content_flags[col] = float(row[col])
        
        return cls(
            title=row.get('Series Name', ''),
            years=row.get('Years', '2000'),
            rating=row.get('Rating', 0.0),
            seasons=row.get('Season', 0.0),
            content_flags=content_flags,
            comments=row.get('Comments', '')
        )
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'Series':
        """Create series from CSV row"""
        content_flags = {}
        flag_columns = ['Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
        
        for col in flag_columns:
            if col in row and pd.notna(row[col]):
                content_flags[col] = float(row[col])
        
        return cls(
            title=row.get('Title', ''),
            years=row.get('Year', '2000'),
            rating=row.get('Rating', 0.0),
            seasons=row.get('Seasons', 0.0),
            content_flags=content_flags,
            comments=row.get('Comments', '')
        )


class DataManager:
    """Enhanced data manager with CSV support and backup functionality"""
    
    def __init__(self, csv_file: str = "Watched_csv.csv"):
        self.csv_file = Path(csv_file)
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.movies: List[Movie] = []
        self.series: List[Series] = []
        
        logger.info(f"DataManager initialized with file: {self.csv_file}")
    
    def create_backup(self) -> bool:
        """Create timestamped backup"""
        try:
            if self.csv_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{self.csv_file.stem}_backup_{timestamp}.csv"
                backup_path = self.backup_dir / backup_name
                shutil.copy2(self.csv_file, backup_path)
                logger.info(f"Backup created: {backup_path}")
                return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
        return False
    
    def load_data(self) -> bool:
        """Load data from CSV file with error handling"""
        try:
            if not self.csv_file.exists():
                logger.warning(f"CSV file not found: {self.csv_file}")
                return False
            
            # Load data from CSV
            df = pd.read_csv(self.csv_file)
            
            # Split into movies and series
            movies_df = df[df['Type'] == 'Movie'].copy()
            series_df = df[df['Type'] == 'Series'].copy()
            
            # Load movies
            self.movies = []
            for _, row in movies_df.iterrows():
                try:
                    movie = Movie.from_csv_row(row)
                    self.movies.append(movie)
                except Exception as e:
                    logger.error(f"Error loading movie row: {e}")
            logger.info(f"Loaded {len(self.movies)} movies")
            
            # Load series
            self.series = []
            for _, row in series_df.iterrows():
                try:
                    series = Series.from_csv_row(row)
                    self.series.append(series)
                except Exception as e:
                    logger.error(f"Error loading series row: {e}")
            logger.info(f"Loaded {len(self.series)} series")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def save_data(self) -> bool:
        """Save data to CSV with backup"""
        try:
            # Create backup first
            self.create_backup()
            
            # Prepare combined data
            all_data = []
            
            # Add movies
            for movie in self.movies:
                movie_dict = movie.to_dict()
                movie_dict['Type'] = 'Movie'
                movie_dict['Seasons'] = None
                all_data.append(movie_dict)
            
            # Add series
            for series in self.series:
                series_dict = series.to_dict()
                series_dict['Type'] = 'Series'
                all_data.append(series_dict)
            
            # Create DataFrame and save
            df = pd.DataFrame(all_data)
            
            # Reorder columns for consistency
            column_order = ['Title', 'Type', 'Year', 'Seasons', 'Rating', 'Comments',
                           'Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
            
            # Only include columns that exist
            available_columns = [col for col in column_order if col in df.columns]
            df = df[available_columns]
            
            df.to_csv(self.csv_file, index=False)
            
            logger.info(f"Data saved to {self.csv_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            'total_movies': len(self.movies),
            'total_series': len(self.series),
            'total_items': len(self.movies) + len(self.series),
            'avg_movie_rating': 0.0,
            'avg_series_rating': 0.0,
            'top_genres': {},
            'family_friendly_series': 0,
            'content_warnings': {}
        }
        
        # Movie statistics
        if self.movies:
            movie_ratings = [m.rating for m in self.movies if m.rating > 0]
            if movie_ratings:
                stats['avg_movie_rating'] = sum(movie_ratings) / len(movie_ratings)
        
        # Series statistics
        if self.series:
            series_ratings = [s.rating for s in self.series if s.rating > 0]
            if series_ratings:
                stats['avg_series_rating'] = sum(series_ratings) / len(series_ratings)
            
            stats['family_friendly_series'] = sum(1 for s in self.series if s.family_friendly)
        
        return stats


# Continue with GUI components in the next part...


# GUI Components

class MediaDialog(QDialog):
    """Enhanced dialog for adding/editing movies and series"""
    
    def __init__(self, parent=None, media_item=None, media_type="Movie"):
        super().__init__(parent)
        self.media_item = media_item
        self.media_type = media_type
        self.is_editing = media_item is not None
        
        self.setWindowTitle(f"{'Edit' if self.is_editing else 'Add'} {media_type}")
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        self.setup_ui()
        self.apply_dark_theme()
        
        if self.is_editing:
            self.populate_fields()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create form
        form_layout = QFormLayout()
        
        # Common fields
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter title...")
        form_layout.addRow("Title:", self.title_edit)
        
        if self.media_type == "Movie":
            self.year_spin = QSpinBox()
            self.year_spin.setRange(1800, datetime.now().year + 5)
            self.year_spin.setValue(2023)
            form_layout.addRow("Year:", self.year_spin)
            
            self.genre_edit = QLineEdit()
            self.genre_edit.setPlaceholderText("Drama, Action, Comedy...")
            form_layout.addRow("Genre:", self.genre_edit)
            
            self.status_combo = QComboBox()
            self.status_combo.addItems(["Watched", "Plan to Watch"])
            form_layout.addRow("Status:", self.status_combo)
            
        else:  # Series
            self.years_edit = QLineEdit()
            self.years_edit.setPlaceholderText("2020-2023 or 2020")
            form_layout.addRow("Years:", self.years_edit)
            
            self.seasons_spin = QDoubleSpinBox()
            self.seasons_spin.setRange(0, 50)
            self.seasons_spin.setDecimals(1)
            form_layout.addRow("Seasons:", self.seasons_spin)
            
            self.episodes_spin = QSpinBox()
            self.episodes_spin.setRange(0, 1000)
            form_layout.addRow("Episodes Watched:", self.episodes_spin)
            
            self.genre_edit = QLineEdit()
            self.genre_edit.setPlaceholderText("Drama, Sci-Fi, Comedy...")
            form_layout.addRow("Genre:", self.genre_edit)
            
            self.language_edit = QLineEdit()
            self.language_edit.setText("English")
            form_layout.addRow("Language:", self.language_edit)
        
        # Rating
        self.rating_spin = QDoubleSpinBox()
        self.rating_spin.setRange(0, 11)
        self.rating_spin.setDecimals(1)
        self.rating_spin.setSuffix("/10")
        form_layout.addRow("Rating:", self.rating_spin)
        
        # Comments
        self.comments_edit = QTextEdit()
        self.comments_edit.setMaximumHeight(80)
        self.comments_edit.setPlaceholderText("Optional comments...")
        form_layout.addRow("Comments:", self.comments_edit)
        
        layout.addLayout(form_layout)
        
        # Content flags section
        flags_group = QGroupBox("Content Flags (0-5 scale)")
        flags_layout = QGridLayout(flags_group)
        
        self.content_flags = {}
        flag_names = ['Romantic', 'Comedy', 'Action', 'Intimacy', 'Abusive', 'Naked']
        
        for i, flag in enumerate(flag_names):
            row = i // 2
            col = (i % 2) * 2
            
            label = QLabel(f"{flag}:")
            spin = QDoubleSpinBox()
            spin.setRange(0, 5)
            spin.setDecimals(1)
            
            flags_layout.addWidget(label, row, col)
            flags_layout.addWidget(spin, row, col + 1)
            
            self.content_flags[flag] = spin
        
        layout.addWidget(flags_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def apply_dark_theme(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, 
            QComboBox:focus, QTextEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QGroupBox {
                border: 2px solid #555555;
                border-radius: 8px;
                margin: 10px 0;
                padding-top: 20px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
        """)
    
    def populate_fields(self):
        """Populate fields when editing"""
        if not self.media_item:
            return
        
        self.title_edit.setText(self.media_item.title)
        self.rating_spin.setValue(self.media_item.rating)
        self.comments_edit.setText(getattr(self.media_item, 'comments', ''))
        
        if isinstance(self.media_item, Movie):
            self.year_spin.setValue(int(self.media_item.year))
            self.genre_edit.setText(self.media_item.genre)
            self.status_combo.setCurrentText(self.media_item.status)
        
        elif isinstance(self.media_item, Series):
            self.years_edit.setText(self.media_item.years)
            self.seasons_spin.setValue(self.media_item.seasons)
            self.episodes_spin.setValue(self.media_item.episodes_watched)
            self.genre_edit.setText(self.media_item.genre)
            self.language_edit.setText(self.media_item.language)
        
        # Populate content flags
        for flag_name, spin in self.content_flags.items():
            if flag_name in self.media_item.content_flags:
                spin.setValue(self.media_item.content_flags[flag_name])
    
    def get_media_item(self):
        """Create media item from form data"""
        try:
            # Get content flags
            content_flags = {}
            for flag_name, spin in self.content_flags.items():
                if spin.value() > 0:
                    content_flags[flag_name] = spin.value()
            
            if self.media_type == "Movie":
                return Movie(
                    title=self.title_edit.text(),
                    year=self.year_spin.value(),
                    rating=self.rating_spin.value(),
                    genre=self.genre_edit.text(),
                    status=self.status_combo.currentText(),
                    content_flags=content_flags,
                    comments=self.comments_edit.toPlainText()
                )
            else:  # Series
                return Series(
                    title=self.title_edit.text(),
                    years=self.years_edit.text(),
                    rating=self.rating_spin.value(),
                    seasons=self.seasons_spin.value(),
                    episodes_watched=self.episodes_spin.value(),
                    genre=self.genre_edit.text(),
                    language=self.language_edit.text(),
                    content_flags=content_flags,
                    comments=self.comments_edit.toPlainText()
                )
        except Exception as e:
            logger.error(f"Error creating media item: {e}")
            QMessageBox.critical(self, "Error", f"Error creating {self.media_type.lower()}: {str(e)}")
            return None


class StatisticsWidget(QWidget):
    """Enhanced statistics dashboard"""
    
    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_ui(self):
        """Setup statistics UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📊 Statistics Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Stats grid
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        
        # Create stat cards
        stat_names = [
            ("Total Movies", "total_movies"),
            ("Total Series", "total_series"),
            ("Total Items", "total_items"),
            ("Avg Movie Rating", "avg_movie_rating"),
            ("Avg Series Rating", "avg_series_rating"),
            ("Family Friendly Series", "family_friendly_series")
        ]
        
        for i, (name, key) in enumerate(stat_names):
            row = i // 2
            col = i % 2
            
            card = self.create_stat_card(name, "0")
            stats_layout.addWidget(card, row, col)
            self.stats_labels[key] = card.findChild(QLabel, "value")
        
        layout.addLayout(stats_layout)
        
        # Content warnings section
        warnings_group = QGroupBox("Content Analysis")
        warnings_layout = QVBoxLayout(warnings_group)
        
        self.warnings_text = QTextEdit()
        self.warnings_text.setMaximumHeight(150)
        self.warnings_text.setReadOnly(True)
        warnings_layout.addWidget(self.warnings_text)
        
        layout.addWidget(warnings_group)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Statistics")
        refresh_btn.clicked.connect(self.update_statistics)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
    
    def create_stat_card(self, title: str, value: str) -> QGroupBox:
        """Create a statistics card"""
        card = QGroupBox()
        card.setFixedHeight(80)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card
    
    def apply_dark_theme(self):
        """Apply dark theme to statistics"""
        self.setStyleSheet("""
            QGroupBox {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 8px;
                margin: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QLabel {
                color: #ffffff;
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 10px;
            }
        """)
    
    def update_statistics(self):
        """Update all statistics"""
        try:
            stats = self.data_manager.get_statistics()
            
            # Update basic stats
            self.stats_labels["total_movies"].setText(str(stats["total_movies"]))
            self.stats_labels["total_series"].setText(str(stats["total_series"]))
            self.stats_labels["total_items"].setText(str(stats["total_items"]))
            self.stats_labels["avg_movie_rating"].setText(f"{stats['avg_movie_rating']:.1f}")
            self.stats_labels["avg_series_rating"].setText(f"{stats['avg_series_rating']:.1f}")
            self.stats_labels["family_friendly_series"].setText(str(stats["family_friendly_series"]))
            
            # Update content analysis
            self.update_content_analysis()
            
            logger.info("Statistics updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            QMessageBox.warning(self, "Error", f"Failed to update statistics: {str(e)}")
    
    def update_content_analysis(self):
        """Update content warnings analysis"""
        try:
            analysis_text = "Content Flag Analysis:\n\n"
            
            # Analyze movies
            if self.data_manager.movies:
                movie_flags = {}
                for movie in self.data_manager.movies:
                    for flag, value in movie.content_flags.items():
                        if flag not in movie_flags:
                            movie_flags[flag] = []
                        movie_flags[flag].append(value)
                
                analysis_text += "Movies:\n"
                for flag, values in movie_flags.items():
                    avg_val = sum(values) / len(values) if values else 0
                    analysis_text += f"  {flag}: {avg_val:.1f}/5 (avg)\n"
            
            # Analyze series
            if self.data_manager.series:
                series_flags = {}
                for series in self.data_manager.series:
                    for flag, value in series.content_flags.items():
                        if flag not in series_flags:
                            series_flags[flag] = []
                        series_flags[flag].append(value)
                
                analysis_text += "\nSeries:\n"
                for flag, values in series_flags.items():
                    avg_val = sum(values) / len(values) if values else 0
                    analysis_text += f"  {flag}: {avg_val:.1f}/5 (avg)\n"
                
                # Family friendly analysis
                total_series = len(self.data_manager.series)
                family_friendly = sum(1 for s in self.data_manager.series if s.family_friendly)
                percentage = (family_friendly / total_series * 100) if total_series > 0 else 0
                analysis_text += f"\nFamily Friendly: {family_friendly}/{total_series} ({percentage:.1f}%)"
            
            self.warnings_text.setText(analysis_text)
            
        except Exception as e:
            logger.error(f"Error updating content analysis: {e}")
            self.warnings_text.setText("Error loading content analysis")


# Continue with MainWindow class...


class MainWindow(QMainWindow):
    """Enhanced main window with tabbed interface for movies and series"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        
        self.setWindowTitle("Note-E-Movie - Personal Entertainment Library")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setup_ui()
        self.apply_dark_theme()
        self.load_data()
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(300000)  # Auto-save every 5 minutes
        
        logger.info("MainWindow initialized successfully")
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Movies tab
        self.movies_tab = self.create_movies_tab()
        self.tab_widget.addTab(self.movies_tab, "🎬 Movies")
        
        # Series tab
        self.series_tab = self.create_series_tab()
        self.tab_widget.addTab(self.series_tab, "📺 Series")
        
        # Statistics tab
        self.stats_widget = StatisticsWidget(self.data_manager)
        self.tab_widget.addTab(self.stats_widget, "📊 Statistics")
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Import CSV...", self)
        import_action.triggered.connect(self.import_excel)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export CSV...", self)
        export_action.triggered.connect(self.export_excel)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        add_movie_action = QAction("Add Movie", self)
        add_movie_action.setShortcut("Ctrl+M")
        add_movie_action.triggered.connect(self.add_movie)
        edit_menu.addAction(add_movie_action)
        
        add_series_action = QAction("Add Series", self)
        add_series_action.setShortcut("Ctrl+T")
        add_series_action.triggered.connect(self.add_series)
        edit_menu.addAction(add_series_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh All", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        view_menu.addAction(refresh_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        backup_action = QAction("Create Backup", self)
        backup_action.triggered.connect(self.create_backup)
        tools_menu.addAction(backup_action)
        
        logs_action = QAction("View Logs", self)
        logs_action.triggered.connect(self.view_logs)
        tools_menu.addAction(logs_action)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        
        # Add buttons
        add_movie_btn = QPushButton("➕ Add Movie")
        add_movie_btn.clicked.connect(self.add_movie)
        toolbar.addWidget(add_movie_btn)
        
        add_series_btn = QPushButton("➕ Add Series")
        add_series_btn.clicked.connect(self.add_series)
        toolbar.addWidget(add_series_btn)
        
        toolbar.addSeparator()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_data)
        toolbar.addWidget(save_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_all)
        toolbar.addWidget(refresh_btn)
    
    def create_movies_tab(self) -> QWidget:
        """Create movies management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search and filter section
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Search:")
        self.movie_search = QLineEdit()
        self.movie_search.setPlaceholderText("Search movies...")
        self.movie_search.textChanged.connect(self.filter_movies)
        
        genre_label = QLabel("Genre:")
        self.movie_genre_filter = QComboBox()
        self.movie_genre_filter.addItem("All Genres")
        self.movie_genre_filter.currentTextChanged.connect(self.filter_movies)
        
        status_label = QLabel("Status:")
        self.movie_status_filter = QComboBox()
        self.movie_status_filter.addItems(["All", "Watched", "Plan to Watch"])
        self.movie_status_filter.currentTextChanged.connect(self.filter_movies)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.movie_search)
        search_layout.addWidget(genre_label)
        search_layout.addWidget(self.movie_genre_filter)
        search_layout.addWidget(status_label)
        search_layout.addWidget(self.movie_status_filter)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)
        
        # Movies table
        self.movies_table = QTableWidget()
        self.movies_table.setColumnCount(9)
        self.movies_table.setHorizontalHeaderLabels([
            "Title", "Year", "Genre", "Rating", "Status", "Content Warnings", 
            "Comments", "Date Added", "Actions"
        ])
        
        # Configure table
        header = self.movies_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        
        self.movies_table.setAlternatingRowColors(True)
        self.movies_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.movies_table)
        
        return tab
    
    def create_series_tab(self) -> QWidget:
        """Create series management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search and filter section
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Search:")
        self.series_search = QLineEdit()
        self.series_search.setPlaceholderText("Search series...")
        self.series_search.textChanged.connect(self.filter_series)
        
        genre_label = QLabel("Genre:")
        self.series_genre_filter = QComboBox()
        self.series_genre_filter.addItem("All Genres")
        self.series_genre_filter.currentTextChanged.connect(self.filter_series)
        
        family_label = QLabel("Family Friendly:")
        self.series_family_filter = QComboBox()
        self.series_family_filter.addItems(["All", "Yes", "No"])
        self.series_family_filter.currentTextChanged.connect(self.filter_series)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.series_search)
        search_layout.addWidget(genre_label)
        search_layout.addWidget(self.series_genre_filter)
        search_layout.addWidget(family_label)
        search_layout.addWidget(self.series_family_filter)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)
        
        # Series table
        self.series_table = QTableWidget()
        self.series_table.setColumnCount(11)
        self.series_table.setHorizontalHeaderLabels([
            "Title", "Years", "Seasons", "Episodes", "Rating", "Genre", 
            "Language", "Family Friendly", "Content Warnings", "Comments", "Actions"
        ])
        
        # Configure table
        header = self.series_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        
        self.series_table.setAlternatingRowColors(True)
        self.series_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.series_table)
        
        return tab
    
    def apply_dark_theme(self):
        """Apply comprehensive dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #505050;
            }
            QTableWidget {
                background-color: #353535;
                alternate-background-color: #404040;
                color: #ffffff;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QLabel {
                color: #ffffff;
            }
            QMenuBar {
                background-color: #404040;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #4CAF50;
            }
            QMenu {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
            QToolBar {
                background-color: #404040;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            QStatusBar {
                background-color: #404040;
                color: #ffffff;
                border-top: 1px solid #555555;
            }
        """)
    
    def load_data(self):
        """Load data and populate tables"""
        try:
            self.data_manager.load_data()
            self.populate_movies_table()
            self.populate_series_table()
            self.update_filters()
            self.stats_widget.update_statistics()
            
            self.status_bar.showMessage(
                f"Loaded {len(self.data_manager.movies)} movies and "
                f"{len(self.data_manager.series)} series"
            )
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
    
    def populate_movies_table(self):
        """Populate movies table with data"""
        try:
            self.movies_table.setRowCount(len(self.data_manager.movies))
            
            for row, movie in enumerate(self.data_manager.movies):
                # Basic info
                self.movies_table.setItem(row, 0, QTableWidgetItem(movie.title))
                self.movies_table.setItem(row, 1, QTableWidgetItem(movie.year))
                self.movies_table.setItem(row, 2, QTableWidgetItem(movie.genre))
                self.movies_table.setItem(row, 3, QTableWidgetItem(f"{movie.rating:.1f}"))
                self.movies_table.setItem(row, 4, QTableWidgetItem(movie.status))
                
                # Content warnings
                warnings = movie.get_content_warnings()
                warnings_text = ", ".join(warnings) if warnings else "None"
                self.movies_table.setItem(row, 5, QTableWidgetItem(warnings_text))
                
                self.movies_table.setItem(row, 6, QTableWidgetItem(movie.comments))
                self.movies_table.setItem(row, 7, QTableWidgetItem(movie.date_added))
                
                # Action buttons
                actions_widget = self.create_action_buttons("movie", row)
                self.movies_table.setCellWidget(row, 8, actions_widget)
            
            self.movies_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error populating movies table: {e}")
    
    def populate_series_table(self):
        """Populate series table with data"""
        try:
            self.series_table.setRowCount(len(self.data_manager.series))
            
            for row, series in enumerate(self.data_manager.series):
                # Basic info
                self.series_table.setItem(row, 0, QTableWidgetItem(series.title))
                self.series_table.setItem(row, 1, QTableWidgetItem(series.years))
                self.series_table.setItem(row, 2, QTableWidgetItem(f"{series.seasons:.1f}"))
                self.series_table.setItem(row, 3, QTableWidgetItem(str(series.episodes_watched)))
                self.series_table.setItem(row, 4, QTableWidgetItem(f"{series.rating:.1f}"))
                self.series_table.setItem(row, 5, QTableWidgetItem(series.genre))
                self.series_table.setItem(row, 6, QTableWidgetItem(series.language))
                
                # Family friendly
                family_text = "Yes" if series.family_friendly else "No"
                self.series_table.setItem(row, 7, QTableWidgetItem(family_text))
                
                # Content warnings
                warnings = series.get_content_warnings()
                warnings_text = ", ".join(warnings) if warnings else "None"
                self.series_table.setItem(row, 8, QTableWidgetItem(warnings_text))
                
                self.series_table.setItem(row, 9, QTableWidgetItem(series.comments))
                
                # Action buttons
                actions_widget = self.create_action_buttons("series", row)
                self.series_table.setCellWidget(row, 10, actions_widget)
            
            self.series_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error populating series table: {e}")
    
    def create_action_buttons(self, media_type: str, row: int) -> QWidget:
        """Create action buttons for table rows"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(30, 30)
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda: self.edit_item(media_type, row))
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setToolTip("Delete")
        delete_btn.clicked.connect(lambda: self.delete_item(media_type, row))
        
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        layout.addStretch()
        
        return widget
    
    def update_filters(self):
        """Update filter dropdown options"""
        # Update movie genre filter
        movie_genres = set()
        for movie in self.data_manager.movies:
            if movie.genre:
                movie_genres.add(movie.genre)
        
        self.movie_genre_filter.clear()
        self.movie_genre_filter.addItem("All Genres")
        self.movie_genre_filter.addItems(sorted(movie_genres))
        
        # Update series genre filter
        series_genres = set()
        for series in self.data_manager.series:
            if series.genre:
                series_genres.add(series.genre)
        
        self.series_genre_filter.clear()
        self.series_genre_filter.addItem("All Genres")
        self.series_genre_filter.addItems(sorted(series_genres))
    
    def filter_movies(self):
        """Filter movies table based on search criteria"""
        search_text = self.movie_search.text().lower()
        genre_filter = self.movie_genre_filter.currentText()
        status_filter = self.movie_status_filter.currentText()
        
        for row in range(self.movies_table.rowCount()):
            show_row = True
            
            # Check search text
            if search_text:
                title_item = self.movies_table.item(row, 0)
                if title_item:
                    title = title_item.text().lower()
                    if search_text not in title:
                        show_row = False
                else:
                    show_row = False
            
            # Check genre filter
            if genre_filter != "All Genres":
                genre_item = self.movies_table.item(row, 2)
                if genre_item:
                    genre = genre_item.text()
                    if genre != genre_filter:
                        show_row = False
                else:
                    show_row = False
            
            # Check status filter
            if status_filter != "All":
                status_item = self.movies_table.item(row, 4)
                if status_item:
                    status = status_item.text()
                    if status != status_filter:
                        show_row = False
                else:
                    show_row = False
            
            self.movies_table.setRowHidden(row, not show_row)
    
    def filter_series(self):
        """Filter series table based on search criteria"""
        search_text = self.series_search.text().lower()
        genre_filter = self.series_genre_filter.currentText()
        family_filter = self.series_family_filter.currentText()
        
        for row in range(self.series_table.rowCount()):
            show_row = True
            
            # Check search text
            if search_text:
                title_item = self.series_table.item(row, 0)
                if title_item:
                    title = title_item.text().lower()
                    if search_text not in title:
                        show_row = False
                else:
                    show_row = False
            
            # Check genre filter
            if genre_filter != "All Genres":
                genre_item = self.series_table.item(row, 5)
                if genre_item:
                    genre = genre_item.text()
                    if genre != genre_filter:
                        show_row = False
                else:
                    show_row = False
            
            # Check family friendly filter
            if family_filter != "All":
                family_item = self.series_table.item(row, 7)
                if family_item:
                    family_friendly = family_item.text()
                    if family_filter == "Yes" and family_friendly != "Yes":
                        show_row = False
                    elif family_filter == "No" and family_friendly != "No":
                        show_row = False
                else:
                    show_row = False
            
            self.series_table.setRowHidden(row, not show_row)
    
    # Action methods
    def add_movie(self):
        """Add new movie"""
        dialog = MediaDialog(self, media_type="Movie")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            movie = dialog.get_media_item()
            if movie and isinstance(movie, Movie):
                self.data_manager.movies.append(movie)
                self.populate_movies_table()
                self.update_filters()
                self.stats_widget.update_statistics()
                self.status_bar.showMessage("Movie added successfully")
    
    def add_series(self):
        """Add new series"""
        dialog = MediaDialog(self, media_type="Series")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            series = dialog.get_media_item()
            if series and isinstance(series, Series):
                self.data_manager.series.append(series)
                self.populate_series_table()
                self.update_filters()
                self.stats_widget.update_statistics()
                self.status_bar.showMessage("Series added successfully")
    
    def edit_item(self, media_type: str, row: int):
        """Edit existing item"""
        try:
            if media_type == "movie":
                if 0 <= row < len(self.data_manager.movies):
                    movie = self.data_manager.movies[row]
                    dialog = MediaDialog(self, movie, "Movie")
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        updated_movie = dialog.get_media_item()
                        if updated_movie and isinstance(updated_movie, Movie):
                            self.data_manager.movies[row] = updated_movie
                            self.populate_movies_table()
                            self.stats_widget.update_statistics()
                            self.status_bar.showMessage("Movie updated successfully")
            
            elif media_type == "series":
                if 0 <= row < len(self.data_manager.series):
                    series = self.data_manager.series[row]
                    dialog = MediaDialog(self, series, "Series")
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        updated_series = dialog.get_media_item()
                        if updated_series and isinstance(updated_series, Series):
                            self.data_manager.series[row] = updated_series
                            self.populate_series_table()
                            self.stats_widget.update_statistics()
                            self.status_bar.showMessage("Series updated successfully")
        
        except Exception as e:
            logger.error(f"Error editing {media_type}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit {media_type}: {str(e)}")
    
    def delete_item(self, media_type: str, row: int):
        """Delete item with confirmation"""
        try:
            if media_type == "movie":
                if 0 <= row < len(self.data_manager.movies):
                    movie = self.data_manager.movies[row]
                    reply = QMessageBox.question(
                        self, "Confirm Delete",
                        f"Are you sure you want to delete the movie '{movie.title}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        del self.data_manager.movies[row]
                        self.populate_movies_table()
                        self.stats_widget.update_statistics()
                        self.status_bar.showMessage("Movie deleted successfully")
            
            elif media_type == "series":
                if 0 <= row < len(self.data_manager.series):
                    series = self.data_manager.series[row]
                    reply = QMessageBox.question(
                        self, "Confirm Delete",
                        f"Are you sure you want to delete the series '{series.title}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        del self.data_manager.series[row]
                        self.populate_series_table()
                        self.stats_widget.update_statistics()
                        self.status_bar.showMessage("Series deleted successfully")
        
        except Exception as e:
            logger.error(f"Error deleting {media_type}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete {media_type}: {str(e)}")
    
    def save_data(self):
        """Save data to Excel"""
        try:
            if self.data_manager.save_data():
                self.status_bar.showMessage("Data saved successfully")
                QMessageBox.information(self, "Success", "Data saved successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Failed to save data. Check logs for details.")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
    
    def auto_save(self):
        """Auto-save functionality"""
        try:
            if self.data_manager.save_data():
                self.status_bar.showMessage("Auto-saved", 2000)
                logger.info("Auto-save completed")
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
    
    def refresh_all(self):
        """Refresh all data and views"""
        self.load_data()
        self.status_bar.showMessage("All data refreshed", 2000)
    
    def create_backup(self):
        """Create manual backup"""
        if self.data_manager.create_backup():
            QMessageBox.information(self, "Backup", "Backup created successfully!")
        else:
            QMessageBox.warning(self, "Backup", "Failed to create backup. Check logs for details.")
    
    def import_excel(self):
        """Import data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV File", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Create backup first
                self.data_manager.create_backup()
                
                # Load new data
                old_file = self.data_manager.csv_file
                self.data_manager.csv_file = Path(file_path)
                
                if self.data_manager.load_data():
                    self.populate_movies_table()
                    self.populate_series_table()
                    self.update_filters()
                    self.stats_widget.update_statistics()
                    QMessageBox.information(self, "Import", "Data imported successfully!")
                else:
                    self.data_manager.csv_file = old_file
                    QMessageBox.warning(self, "Import", "Failed to import data.")
                    
            except Exception as e:
                logger.error(f"Import error: {e}")
                QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
    
    def export_excel(self):
        """Export data to CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV File", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Save to specified location
                old_file = self.data_manager.csv_file
                self.data_manager.csv_file = Path(file_path)
                
                if self.data_manager.save_data():
                    QMessageBox.information(self, "Export", "Data exported successfully!")
                else:
                    QMessageBox.warning(self, "Export", "Failed to export data.")
                
                # Restore original file path
                self.data_manager.csv_file = old_file
                
            except Exception as e:
                logger.error(f"Export error: {e}")
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    
    def view_logs(self):
        """View application logs"""
        log_dialog = QDialog(self)
        log_dialog.setWindowTitle("Application Logs")
        log_dialog.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout(log_dialog)
        
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        
        # Read log file
        try:
            with open('note_e_movie.log', 'r') as f:
                log_content = f.read()
                log_text.setText(log_content)
        except FileNotFoundError:
            log_text.setText("No log file found.")
        except Exception as e:
            log_text.setText(f"Error reading log file: {e}")
        
        layout.addWidget(log_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(log_dialog.close)
        layout.addWidget(close_btn)
        
        log_dialog.setStyleSheet(self.styleSheet())
        log_dialog.exec()
    
    def closeEvent(self, event):
        """Handle application close event"""
        reply = QMessageBox.question(
            self, "Save Before Exit",
            "Do you want to save your changes before exiting?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Save:
            self.save_data()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point"""
    # Set environment for high DPI
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("Note-E-Movie")
    app.setApplicationVersion("1.0")
    
    # Set modern style
    app.setStyle('Fusion')
    
    # Create and show main window
    try:
        window = MainWindow()
        window.show()
        
        # Center window on screen
        screen = app.primaryScreen().geometry()
        window_geo = window.geometry()
        window.move(
            (screen.width() - window_geo.width()) // 2,
            (screen.height() - window_geo.height()) // 2
        )
        
        logger.info("Application started successfully")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        QMessageBox.critical(None, "Critical Error", f"Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
