/*
 * Patchbay Canvas engine using QGraphicsView/Scene
 * Copyright (C) 2010-2012 Filipe Coelho <falktx@falktx.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * For a full copy of the GNU General Public License see the COPYING file
 */

#include "canvasline.h"

#include <QtGui/QPainter>

#include "canvasport.h"
#include "canvasportglow.h"

START_NAMESPACE_PATCHCANVAS

CanvasLine::CanvasLine(CanvasPort* item1_, CanvasPort* item2_, QGraphicsItem* parent) :
    QGraphicsLineItem(parent, canvas.scene)
{
    item1 = item1_;
    item2 = item2_;

    m_locked = false;
    m_lineSelected = false;

    setGraphicsEffect(0);
    updateLinePos();
}

CanvasLine::~CanvasLine()
{
    setGraphicsEffect(0);
}

void CanvasLine::deleteFromScene()
{
    canvas.scene->removeItem(this);
    delete this;
}

bool CanvasLine::isLocked() const
{
    return m_locked;
}

void CanvasLine::setLocked(bool yesno)
{
    m_locked = yesno;
}

bool CanvasLine::isLineSelected() const
{
    return m_lineSelected;
}

void CanvasLine::setLineSelected(bool yesno)
{
    if (m_locked)
        return;

    if (options.eyecandy == EYECANDY_FULL)
    {
        if (yesno)
            setGraphicsEffect(new CanvasPortGlow(item1->getPortType(), toGraphicsObject()));
        else
            setGraphicsEffect(0);
    }

    m_lineSelected = yesno;
    updateLineGradient();
}

void CanvasLine::updateLinePos()
{
    if (item1->getPortMode() == PORT_MODE_OUTPUT)
    {
        QLineF line(item1->scenePos().x() + item1->getPortWidth()+12, item1->scenePos().y()+7.5, item2->scenePos().x(), item2->scenePos().y()+7.5);
        setLine(line);

        m_lineSelected = false;
        updateLineGradient();
    }
}

int CanvasLine::type() const
{
    return CanvasLineType;
}

void CanvasLine::updateLineGradient()
{
    short pos1, pos2;
    int pos_top = boundingRect().top();
    int pos_bot = boundingRect().bottom();

    if (item2->scenePos().y() >= item1->scenePos().y())
    {
        pos1 = 0;
        pos2 = 1;
    }
    else
    {
        pos1 = 1;
        pos2 = 0;
    }

    PortType port_type1 = item1->getPortType();
    PortType port_type2 = item2->getPortType();
    QLinearGradient port_gradient(0, pos_top, 0, pos_bot);

    if (port_type1 == PORT_TYPE_AUDIO_JACK)
        port_gradient.setColorAt(pos1, m_lineSelected ? canvas.theme->line_audio_jack_sel : canvas.theme->line_audio_jack);
    else if (port_type1 == PORT_TYPE_MIDI_JACK)
        port_gradient.setColorAt(pos1, m_lineSelected ? canvas.theme->line_midi_jack_sel : canvas.theme->line_midi_jack);
    else if (port_type1 == PORT_TYPE_MIDI_A2J)
        port_gradient.setColorAt(pos1, m_lineSelected ? canvas.theme->line_midi_a2j_sel : canvas.theme->line_midi_a2j);
    else if (port_type1 == PORT_TYPE_MIDI_ALSA)
        port_gradient.setColorAt(pos1, m_lineSelected ? canvas.theme->line_midi_alsa_sel : canvas.theme->line_midi_alsa);

    if (port_type2 == PORT_TYPE_AUDIO_JACK)
        port_gradient.setColorAt(pos2, m_lineSelected ? canvas.theme->line_audio_jack_sel : canvas.theme->line_audio_jack);
    else if (port_type2 == PORT_TYPE_MIDI_JACK)
        port_gradient.setColorAt(pos2, m_lineSelected ? canvas.theme->line_midi_jack_sel : canvas.theme->line_midi_jack);
    else if (port_type2 == PORT_TYPE_MIDI_A2J)
        port_gradient.setColorAt(pos2, m_lineSelected ? canvas.theme->line_midi_a2j_sel : canvas.theme->line_midi_a2j);
    else if (port_type2 == PORT_TYPE_MIDI_ALSA)
        port_gradient.setColorAt(pos2, m_lineSelected ? canvas.theme->line_midi_alsa_sel : canvas.theme->line_midi_alsa);

    setPen(QPen(port_gradient, 2));
}

void CanvasLine::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget)
{
    painter->setRenderHint(QPainter::Antialiasing, bool(options.antialiasing));
    QGraphicsLineItem::paint(painter, option, widget);
}

END_NAMESPACE_PATCHCANVAS
