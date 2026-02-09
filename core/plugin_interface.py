from abc import ABC, abstractmethod
import streamlit as st

class MarketTerminalPlugin(ABC):
    """
    Standard Interface for all Market Terminal Plugins.
    Every tool (Alpha Fusion, Bot, Analyzer) must implement this.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the plugin (e.g., 'Alpha Fusion')"""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category: 'Research', 'Trading', 'Portfolio', 'Risk'"""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Emoji icon for the sidebar"""
        pass

    @abstractmethod
    def render(self, ticker: str):
        """The main Streamlit render function for the plugin."""
        pass
