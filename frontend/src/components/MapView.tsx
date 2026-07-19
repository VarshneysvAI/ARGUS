'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import axios from 'axios';

const KEY_FREE_STYLE = {
  version: 8,
  sources: {
    'public-satellite': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256,
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    }
  },
  layers: [
    {
      id: 'satellite-layer',
      type: 'raster',
      source: 'public-satellite',
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

export default function MapView() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [vessels, setVessels] = useState<any[]>([]);

  useEffect(() => {
    const fetchAis = async () => {
      try {
        const res = await axios.get('http://127.0.0.1:8000/api/ais');
        if (res.data && res.data.data) {
          setVessels(res.data.data);
        }
      } catch {
        // Ignore errors
      }
    };
    
    fetchAis();
    const interval = setInterval(fetchAis, 5000);
    return () => clearInterval(interval);
  }, []);

  const vesselsGeoJson = {
    type: 'FeatureCollection',
    features: vessels.map(v => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [v.lon, v.lat] },
      properties: { name: v.name, mmsi: v.MMSI }
    }))
  };

  const vectorGeoJson = {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [[54.5, 25.5], [56.5, 26.5]]
      },
      properties: {}
    }]
  };

  return (
    <div className="w-full h-full min-h-[400px] relative">
      <Map
        initialViewState={{
          longitude: 55.5,
          latitude: 26.0,
          zoom: 6
        }}
        mapStyle={KEY_FREE_STYLE as never}
        style={{ width: '100%', height: '100%' }}
      >
        
        {/* Disruption Vector */}
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <Source type="geojson" data={vectorGeoJson as any}>
            <Layer 
                id="hormuz-vector" 
                type="line" 
                paint={{'line-color': '#ef4444', 'line-width': 4, 'line-dasharray': [2, 2]}} 
            />
        </Source>

        {/* AIS Vessels Layer (Dots) */}
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <Source type="geojson" data={vesselsGeoJson as any}>
            <Layer 
                id="vessels-layer" 
                type="circle" 
                paint={{
                    'circle-radius': 4,
                    'circle-color': '#06b6d4',
                    'circle-stroke-width': 1,
                    'circle-stroke-color': '#ffffff'
                }} 
            />
        </Source>
      </Map>
    </div>
  );
}
